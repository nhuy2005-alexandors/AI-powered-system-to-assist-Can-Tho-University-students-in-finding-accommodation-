from datetime import datetime, timezone

import pytest
from fastapi import HTTPException

from app.auth.schemas import UserOut
from app.reports.schemas import (
    ModerateReportIn,
    ModerationAction,
    ReportCreate,
    ReportOut,
    ReportReason,
)
from app.reports.service import ReportService


USER = UserOut(id=10, email="student@example.com", name="Student", role="user")
ADMIN = UserOut(id=1, email="admin@example.com", name="Admin", role="admin")


class FakeRisk:
    def __init__(self):
        self.assessed = []

    def assess(self, listing_id, *, persist):
        self.assessed.append((listing_id, persist))
        return type("Assessment", (), {"risk_score": 0.3, "risk_level": "caution"})()


class FakeRepo:
    def __init__(self, listing=None, pending=None):
        self.listing = listing or {"id": 7, "posted_by": None, "status": "active"}
        self.pending = pending
        self.created = []
        self.status_updates = []

    def get_reportable_listing(self, listing_id):
        return self.listing

    def find_pending(self, listing_id, reporter_id):
        return self.pending

    def create(self, listing_id, reporter_id, reason, note):
        self.created.append((listing_id, reporter_id, reason, note))
        return ReportOut(
            id=5,
            listing_id=listing_id,
            reporter_id=reporter_id,
            reason=reason,
            note=note,
            status="pending",
            created_at=datetime.now(timezone.utc),
        )

    def moderate_listing_reports(self, report_id, admin_id, action, note):
        return 7, 2, {"dismiss": "active", "flag": "flagged", "hide": "hidden"}[action]

    def set_listing_status(self, listing_id, status):
        self.status_updates.append((listing_id, status))


def test_submit_report_persists_and_reassesses_risk():
    repo = FakeRepo()
    risk = FakeRisk()
    service = ReportService(repo, risk)

    result = service.submit(
        7,
        USER,
        ReportCreate(reason=ReportReason.scam, note="  Yêu cầu chuyển khoản trước  "),
    )

    assert result.status.value == "pending"
    assert repo.created == [(7, USER.id, "scam", "Yêu cầu chuyển khoản trước")]
    assert risk.assessed == [(7, True)]


def test_submit_rejects_owner_and_duplicate_pending_report():
    owner_service = ReportService(FakeRepo(listing={"id": 7, "posted_by": USER.id, "status": "active"}), FakeRisk())
    with pytest.raises(HTTPException) as owner_error:
        owner_service.submit(7, USER, ReportCreate(reason=ReportReason.other))
    assert owner_error.value.status_code == 400

    existing = ReportOut(
        id=1,
        listing_id=7,
        reporter_id=USER.id,
        reason="expired",
        status="pending",
        created_at=datetime.now(timezone.utc),
    )
    duplicate_service = ReportService(FakeRepo(pending=existing), FakeRisk())
    with pytest.raises(HTTPException) as duplicate_error:
        duplicate_service.submit(7, USER, ReportCreate(reason=ReportReason.expired))
    assert duplicate_error.value.status_code == 409


def test_admin_moderation_resolves_listing_reports_and_reassesses():
    repo = FakeRepo()
    risk = FakeRisk()
    result = ReportService(repo, risk).moderate(
        5,
        ADMIN,
        ModerateReportIn(action=ModerationAction.hide, note="Đã xác minh"),
    )

    assert result.listing_id == 7
    assert result.resolved_reports == 2
    assert result.listing_status == "hidden"
    assert result.risk_level == "caution"
    assert risk.assessed == [(7, True)]
