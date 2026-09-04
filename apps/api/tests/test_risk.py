from datetime import datetime, timezone

import pytest
from fastapi import HTTPException

from app.room_service.risk.scoring import MODEL_VERSION, score_listing
from app.room_service.risk.service import RiskService


def _listing(**overrides):
    value = {
        "id": 12,
        "title": "Phòng trọ sinh viên gần Đại học Cần Thơ",
        "description": "Phòng sạch sẽ, có gác, cho xem phòng trực tiếp và ký hợp đồng rõ ràng.",
        "price": 2_000_000,
        "area": 20,
        "address": "Đường 3/2, Xuân Khánh",
        "district": "Ninh Kiều",
        "images": ["https://example.com/room.jpg"],
        "source": "user",
        "source_url": None,
        "listing_type": "phong_tro",
        "quality_score": 0.9,
        "freshness_score": 0.9,
        "geocode_confidence": "high",
    }
    value.update(overrides)
    return value


def test_safe_listing_has_evaluated_floor_instead_of_unknown_zero():
    now = datetime(2026, 8, 31, tzinfo=timezone.utc)

    result = score_listing(_listing(), district_median_price=2_100_000, now=now)

    assert result.score == 0.01
    assert result.level == "safe"
    assert result.reasons == []
    assert result.evaluated_at == now


def test_scam_language_and_no_inspection_are_suspicious():
    result = score_listing(
        _listing(
            title="Giá sốc, chốt ngay hôm nay",
            description="Đặt cọc trước để giữ chỗ, không cho xem phòng, chỉ giao dịch online.",
        ),
        district_median_price=2_000_000,
    )

    assert result.score >= 0.6
    assert result.level == "suspicious"
    assert {signal.code for signal in result.signals} >= {
        "advance_payment",
        "no_inspection",
        "urgency",
    }


def test_unusually_low_price_is_explained():
    result = score_listing(_listing(price=700_000), district_median_price=2_000_000)

    assert result.score == 0.3
    assert result.level == "caution"
    assert [signal.code for signal in result.signals] == ["price_extreme"]


def test_community_reports_raise_risk_and_explain_why():
    result = score_listing(
        _listing(report_count=1, scam_report_count=1),
        district_median_price=2_000_000,
    )

    assert result.score == 0.3
    assert result.level == "caution"
    assert {signal.code for signal in result.signals} == {
        "community_reports",
        "community_scam_reports",
    }


class FakeRepo:
    def __init__(self, listings, pending=None):
        self.listings = listings
        self.pending = pending or []
        self.saved = []

    def get_listing(self, listing_id):
        return self.listings.get(listing_id)

    def district_median_price(self, listing):
        return 2_000_000

    def save(self, listing_id, result):
        self.saved.append((listing_id, result))

    def pending_ids(self, limit):
        return self.pending[:limit]


def test_preview_does_not_persist_but_assess_does():
    repo = FakeRepo({12: _listing()})
    service = RiskService(repo)

    preview = service.assess(12, persist=False)
    persisted = service.assess(12, persist=True)

    assert preview.persisted is False
    assert persisted.persisted is True
    assert persisted.model_version == MODEL_VERSION
    assert len(repo.saved) == 1
    assert repo.saved[0][0] == 12


def test_missing_listing_returns_404():
    service = RiskService(FakeRepo({}))

    with pytest.raises(HTTPException) as error:
        service.assess(404, persist=False)

    assert error.value.status_code == 404


def test_batch_reports_levels_and_failed_ids():
    repo = FakeRepo(
        {
            1: _listing(id=1),
            2: _listing(
                id=2,
                description="Cọc ngay, chuyển khoản trước. Không cho xem phòng, chỉ giao dịch online.",
            ),
        },
        pending=[1, 2, 999],
    )

    result = RiskService(repo).assess_pending(10)

    assert result.processed == 2
    assert result.safe == 1
    assert result.suspicious == 1
    assert result.failed_listing_ids == [999]
