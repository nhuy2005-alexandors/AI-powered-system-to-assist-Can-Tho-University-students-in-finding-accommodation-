from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any


MODEL_VERSION = "room-risk-rules-v1"


@dataclass(frozen=True, slots=True)
class Signal:
    code: str
    message: str
    weight: float


@dataclass(frozen=True, slots=True)
class ScoreResult:
    score: float
    level: str
    signals: list[Signal]
    evaluated_at: datetime

    @property
    def reasons(self) -> list[str]:
        return [signal.message for signal in self.signals]


def normalize_text(value: object) -> str:
    text = unicodedata.normalize("NFD", str(value or "").lower())
    text = "".join(character for character in text if unicodedata.category(character) != "Mn")
    text = text.replace("đ", "d")
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9\s]", " ", text)).strip()


def level_for_score(score: float) -> str:
    if score < 0.3:
        return "safe"
    if score < 0.6:
        return "caution"
    return "suspicious"


def _contains_any(text: str, phrases: tuple[str, ...]) -> bool:
    return any(phrase in text for phrase in phrases)


def score_listing(
    listing: dict[str, Any],
    *,
    district_median_price: float | None = None,
    now: datetime | None = None,
) -> ScoreResult:
    """Explainable cold-start risk score; replaceable by an ML provider later."""

    now = now or datetime.now(timezone.utc)
    combined_text = normalize_text(
        f"{listing.get('title', '')} {listing.get('description', '')}"
    )
    signals: list[Signal] = []

    def add(code: str, message: str, weight: float) -> None:
        signals.append(Signal(code, message, weight))

    if _contains_any(
        combined_text,
        (
            "chuyen khoan truoc",
            "dat coc truoc",
            "coc giu cho",
            "coc ngay",
            "gui tien truoc",
        ),
    ):
        add("advance_payment", "Yêu cầu chuyển tiền hoặc đặt cọc trước", 0.32)
    if _contains_any(
        combined_text,
        ("khong can xem phong", "khong cho xem phong", "chi giao dich online"),
    ):
        add("no_inspection", "Có dấu hiệu né tránh việc xem phòng trực tiếp", 0.28)
    if _contains_any(
        combined_text,
        ("gia soc", "re bat ngo", "chot ngay", "gap trong ngay", "chi hom nay"),
    ):
        add("urgency", "Nội dung thúc ép hoặc quảng cáo giá bất thường", 0.10)

    price = listing.get("price")
    if price and district_median_price and district_median_price > 0:
        ratio = float(price) / district_median_price
        if ratio < 0.45:
            add("price_extreme", "Giá thấp hơn rất nhiều so với mặt bằng cùng khu vực", 0.30)
        elif ratio < 0.65:
            add("price_low", "Giá thấp đáng kể so với mặt bằng cùng khu vực", 0.18)

    if not listing.get("address") or not listing.get("district"):
        add("missing_location", "Thiếu địa chỉ hoặc khu vực rõ ràng", 0.10)
    if not listing.get("images"):
        add("missing_images", "Tin không có hình ảnh kiểm chứng", 0.09)
    if listing.get("source") != "user" and not listing.get("source_url"):
        add("missing_source", "Không có đường dẫn nguồn để đối chiếu", 0.08)
    if len(normalize_text(listing.get("description"))) < 35:
        add("short_description", "Mô tả quá ngắn, thiếu thông tin kiểm chứng", 0.06)

    quality = listing.get("quality_score")
    if quality is not None and float(quality) < 0.35:
        add("low_quality", "Điểm chất lượng dữ liệu thấp", 0.13)
    freshness = listing.get("freshness_score")
    if freshness is not None and float(freshness) < 0.25:
        add("stale_listing", "Tin đã cũ hoặc ít được cập nhật", 0.08)
    if str(listing.get("geocode_confidence") or "").lower() in {"", "low"}:
        add("weak_geocode", "Vị trí có độ tin cậy thấp", 0.05)

    report_count = int(listing.get("report_count") or 0)
    if report_count:
        report_weight = min(0.35, 0.13 + 0.05 * report_count)
        add(
            "community_reports",
            f"Có {report_count} báo cáo đã được cộng đồng gửi và chưa bị bác bỏ",
            report_weight,
        )
    scam_report_count = int(listing.get("scam_report_count") or 0)
    if scam_report_count:
        add(
            "community_scam_reports",
            f"Có {scam_report_count} báo cáo nghi ngờ lừa đảo",
            0.12,
        )

    # 0.01 means "evaluated and no material signal"; database default 0 remains unknown.
    score = max(0.01, min(0.95, sum(signal.weight for signal in signals)))
    return ScoreResult(
        score=round(score, 4),
        level=level_for_score(score),
        signals=signals,
        evaluated_at=now,
    )
