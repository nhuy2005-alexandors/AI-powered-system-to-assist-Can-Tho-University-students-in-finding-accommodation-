from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.engine import Engine

from ...auth import require_admin
from .repo import RiskRepository
from .schemas import RiskAssessment, RiskBatchResponse
from .service import RiskService

router = APIRouter(prefix="/risk", tags=["room-risk"])
_service: RiskService | None = None


def init_risk(engine: Engine) -> None:
    global _service
    _service = RiskService(RiskRepository(engine))


def get_service() -> RiskService:
    if _service is None:
        raise HTTPException(503, "Risk service chưa khởi tạo")
    return _service


@router.get("/listings/{listing_id}", response_model=RiskAssessment)
def preview_listing_risk(
    listing_id: int,
    service: RiskService = Depends(get_service),
):
    """Tính thử trên dữ liệu hiện tại, không ghi database."""
    return service.assess(listing_id, persist=False)


@router.post("/listings/{listing_id}/assess", response_model=RiskAssessment)
def assess_listing_risk(
    listing_id: int,
    _admin=Depends(require_admin),
    service: RiskService = Depends(get_service),
):
    """Admin đánh giá và lưu kết quả vào aggregated_listings."""
    return service.assess(listing_id, persist=True)


@router.post("/assess-pending", response_model=RiskBatchResponse)
def assess_pending_listings(
    limit: int = Query(default=100, ge=1, le=1000),
    _admin=Depends(require_admin),
    service: RiskService = Depends(get_service),
):
    return service.assess_pending(limit)
