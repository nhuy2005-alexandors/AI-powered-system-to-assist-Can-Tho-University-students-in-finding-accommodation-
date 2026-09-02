from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError

from ..auth.schemas import UserOut
from ..room_service.risk.service import RiskService
from .repo import ReportRepository
from .schemas import (
    AdminDashboardSummary,
    AdminListingItem,
    AdminListingList,
    AdminListingStatus,
    AdminUserList,
    AdminReportList,
    ModerateReportIn,
    ModerationResult,
    ReportCreate,
    ReportOut,
    ReportStatus,
)


class ReportService:
    def __init__(self, repo: ReportRepository, risk: RiskService):
        self.repo = repo
        self.risk = risk

    def submit(self, listing_id: int, user: UserOut, body: ReportCreate) -> ReportOut:
        listing = self.repo.get_reportable_listing(listing_id)
        if listing is None:
            raise HTTPException(404, "Không tìm thấy tin nhà trọ")
        if listing["status"] in {"expired", "hidden"}:
            raise HTTPException(409, "Tin này không còn nhận báo cáo")
        if listing.get("posted_by") == user.id:
            raise HTTPException(400, "Bạn không thể báo cáo tin do mình đăng")
        if self.repo.find_pending(listing_id, user.id):
            raise HTTPException(409, "Bạn đã báo cáo tin này và đang chờ Admin xử lý")
        try:
            report = self.repo.create(
                listing_id,
                user.id,
                body.reason.value,
                body.note.strip() if body.note and body.note.strip() else None,
            )
        except IntegrityError as exc:
            raise HTTPException(409, "Bạn đã báo cáo tin này và đang chờ Admin xử lý") from exc
        assessment = self.risk.assess(listing_id, persist=True)
        if assessment.risk_level == "suspicious":
            self.repo.set_listing_status(listing_id, "flagged")
        return report

    def mine(self, user_id: int) -> list[ReportOut]:
        return self.repo.by_reporter(user_id)

    def admin_reports(
        self,
        status: ReportStatus | None,
        page: int,
        size: int,
    ) -> AdminReportList:
        total, items = self.repo.admin_list(
            status.value if status else None,
            size,
            (page - 1) * size,
        )
        return AdminReportList(total=total, items=items)

    def moderate(self, report_id: int, admin: UserOut, body: ModerateReportIn) -> ModerationResult:
        value = self.repo.moderate_listing_reports(
            report_id,
            admin.id,
            body.action.value,
            body.note.strip() if body.note and body.note.strip() else None,
        )
        if value is None:
            raise HTTPException(404, "Không tìm thấy báo cáo")
        listing_id, resolved, listing_status = value
        if resolved == 0:
            raise HTTPException(409, "Báo cáo này đã được xử lý")
        assessment = self.risk.assess(listing_id, persist=True)
        if body.action.value == "dismiss" and assessment.risk_level == "suspicious":
            self.repo.set_listing_status(listing_id, "flagged")
            listing_status = "flagged"
        return ModerationResult(
            listing_id=listing_id,
            action=body.action,
            resolved_reports=resolved,
            listing_status=listing_status,
            risk_score=assessment.risk_score,
            risk_level=assessment.risk_level,
        )

    def summary(self) -> AdminDashboardSummary:
        return AdminDashboardSummary(**self.repo.dashboard_summary())

    def listings(
        self,
        query: str | None,
        status: AdminListingStatus | None,
        page: int,
        size: int,
    ) -> AdminListingList:
        total, items = self.repo.admin_listings(
            query.strip() if query and query.strip() else None,
            status.value if status else None,
            size,
            (page - 1) * size,
        )
        return AdminListingList(total=total, items=items)

    def update_listing_status(self, listing_id: int, status: AdminListingStatus) -> AdminListingItem:
        if not self.repo.set_admin_listing_status(listing_id, status.value):
            raise HTTPException(404, "Không tìm thấy bài tin")
        item = self.repo.admin_listing(listing_id)
        if item is None:
            raise HTTPException(404, "Không tìm thấy bài tin")
        return item

    def users(self, query: str | None, page: int, size: int) -> AdminUserList:
        total, items = self.repo.admin_users(
            query.strip() if query and query.strip() else None,
            size,
            (page - 1) * size,
        )
        return AdminUserList(total=total, items=items)
