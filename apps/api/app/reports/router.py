from fastapi import APIRouter, Depends, Query
from sqlalchemy.engine import Engine

from ..auth import get_current_user, require_admin
from ..auth.schemas import UserOut
from ..room_service.risk.repo import RiskRepository
from ..room_service.risk.service import RiskService
from .repo import ReportRepository
from .schemas import (
    AdminDashboardSummary,
    AdminListingItem,
    AdminListingList,
    AdminListingStatus,
    AdminListingStatusIn,
    AdminReportList,
    AdminUserList,
    ModerateReportIn,
    ModerationResult,
    ReportCreate,
    ReportOut,
    ReportStatus,
)
from .service import ReportService

router = APIRouter(tags=["reports"])
_service: ReportService | None = None


def init_reports(engine: Engine) -> None:
    global _service
    _service = ReportService(ReportRepository(engine), RiskService(RiskRepository(engine)))


def get_service() -> ReportService:
    if _service is None:
        from fastapi import HTTPException

        raise HTTPException(503, "Report service chưa khởi tạo")
    return _service


@router.post("/listings/{listing_id}/report", response_model=ReportOut, status_code=201)
def submit_report(
    listing_id: int,
    body: ReportCreate,
    user: UserOut = Depends(get_current_user),
    service: ReportService = Depends(get_service),
):
    return service.submit(listing_id, user, body)


@router.get("/reports/mine", response_model=list[ReportOut])
def my_reports(
    user: UserOut = Depends(get_current_user),
    service: ReportService = Depends(get_service),
):
    return service.mine(user.id)


@router.get("/admin/reports", response_model=AdminReportList)
def admin_reports(
    status: ReportStatus | None = ReportStatus.pending,
    page: int = Query(default=1, ge=1),
    size: int = Query(default=50, ge=1, le=100),
    _admin: UserOut = Depends(require_admin),
    service: ReportService = Depends(get_service),
):
    return service.admin_reports(status, page, size)


@router.patch("/admin/reports/{report_id}", response_model=ModerationResult)
def moderate_report(
    report_id: int,
    body: ModerateReportIn,
    admin: UserOut = Depends(require_admin),
    service: ReportService = Depends(get_service),
):
    return service.moderate(report_id, admin, body)


@router.get("/admin/summary", response_model=AdminDashboardSummary)
def admin_summary(
    _admin: UserOut = Depends(require_admin),
    service: ReportService = Depends(get_service),
):
    return service.summary()


@router.get("/admin/listings", response_model=AdminListingList)
def admin_listings(
    q: str | None = None,
    status: AdminListingStatus | None = None,
    page: int = Query(default=1, ge=1),
    size: int = Query(default=50, ge=1, le=100),
    _admin: UserOut = Depends(require_admin),
    service: ReportService = Depends(get_service),
):
    return service.listings(q, status, page, size)


@router.patch("/admin/listings/{listing_id}/status", response_model=AdminListingItem)
def update_admin_listing_status(
    listing_id: int,
    body: AdminListingStatusIn,
    _admin: UserOut = Depends(require_admin),
    service: ReportService = Depends(get_service),
):
    return service.update_listing_status(listing_id, body.status)


@router.get("/admin/users", response_model=AdminUserList)
def admin_users(
    q: str | None = None,
    page: int = Query(default=1, ge=1),
    size: int = Query(default=50, ge=1, le=100),
    _admin: UserOut = Depends(require_admin),
    service: ReportService = Depends(get_service),
):
    return service.users(q, page, size)
