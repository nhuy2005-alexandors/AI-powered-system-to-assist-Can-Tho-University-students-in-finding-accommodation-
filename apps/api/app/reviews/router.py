from fastapi import APIRouter, Depends, Query
from sqlalchemy.engine import Engine

from ..auth import get_current_user, require_admin
from ..auth.schemas import UserOut
from .repo import ReviewRepository
from .schemas import (
    AdminReviewList,
    ReviewCreate,
    ReviewList,
    ReviewModerationIn,
    ReviewOut,
)
from .service import ReviewService


router = APIRouter(tags=["reviews"])
_service: ReviewService | None = None


def init_reviews(engine: Engine) -> None:
    global _service
    _service = ReviewService(ReviewRepository(engine))


def get_service() -> ReviewService:
    if _service is None:
        from fastapi import HTTPException

        raise HTTPException(503, "Review service chưa khởi tạo")
    return _service


@router.get("/listings/{listing_id}/reviews", response_model=ReviewList)
def listing_reviews(
    listing_id: int,
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
    service: ReviewService = Depends(get_service),
):
    return service.list(listing_id, page, size)


@router.post("/listings/{listing_id}/reviews", response_model=ReviewOut, status_code=201)
def submit_review(
    listing_id: int,
    body: ReviewCreate,
    user: UserOut = Depends(get_current_user),
    service: ReviewService = Depends(get_service),
):
    return service.submit(listing_id, user, body)


@router.get("/admin/reviews/flagged", response_model=AdminReviewList)
def flagged_reviews(
    page: int = Query(default=1, ge=1),
    size: int = Query(default=50, ge=1, le=100),
    _admin: UserOut = Depends(require_admin),
    service: ReviewService = Depends(get_service),
):
    return service.flagged(page, size)


@router.patch("/admin/reviews/{review_id}", response_model=ReviewOut)
def moderate_review(
    review_id: int,
    body: ReviewModerationIn,
    _admin: UserOut = Depends(require_admin),
    service: ReviewService = Depends(get_service),
):
    return service.moderate(review_id, body.action)
