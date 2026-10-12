from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError

from ..auth.schemas import UserOut
from .repo import ReviewRepository
from .schemas import AdminReviewList, ReviewCreate, ReviewList, ReviewOut, ReviewModerationAction
from .sentiment import VietnameseReviewSentimentModel, sentiment_model


class ReviewService:
    def __init__(
        self,
        repo: ReviewRepository,
        model: VietnameseReviewSentimentModel = sentiment_model,
    ):
        self.repo = repo
        self.model = model

    def list(self, listing_id: int, page: int, size: int) -> ReviewList:
        if self.repo.get_listing(listing_id) is None:
            raise HTTPException(404, "Không tìm thấy tin nhà trọ")
        return self.repo.list_for_listing(listing_id, size, (page - 1) * size)

    def submit(self, listing_id: int, user: UserOut, body: ReviewCreate) -> ReviewOut:
        listing = self.repo.get_listing(listing_id)
        if listing is None:
            raise HTTPException(404, "Không tìm thấy tin nhà trọ")
        if listing["status"] in {"expired", "hidden"}:
            raise HTTPException(409, "Tin này không còn nhận đánh giá")
        if listing.get("posted_by") == user.id:
            raise HTTPException(400, "Bạn không thể tự đánh giá tin do mình đăng")

        comment = " ".join(body.comment.split())
        if len(comment) < 10:
            raise HTTPException(422, "Bình luận cần có ít nhất 10 ký tự")
        prediction = self.model.predict(comment)
        moderation_status = "flagged" if prediction.is_flagged else "published"
        try:
            return self.repo.create(
                listing_id,
                user.id,
                body.rating,
                comment,
                prediction.label,
                prediction.negative_score,
                moderation_status,
                prediction.model_version,
            )
        except IntegrityError as exc:
            raise HTTPException(409, "Bạn đã đánh giá phòng này") from exc

    def flagged(self, page: int, size: int) -> AdminReviewList:
        total, items = self.repo.flagged(size, (page - 1) * size)
        return AdminReviewList(total=total, items=items)

    def moderate(self, review_id: int, action: ReviewModerationAction) -> ReviewOut:
        status = "published" if action == ReviewModerationAction.approve else "hidden"
        review = self.repo.moderate(review_id, status)
        if review is None:
            raise HTTPException(404, "Không tìm thấy đánh giá")
        return review
