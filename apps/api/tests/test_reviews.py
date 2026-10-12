from datetime import datetime, timezone

import pytest
from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError

from app.auth.schemas import UserOut
from app.reviews.schemas import ReviewCreate, ReviewOut
from app.reviews.sentiment import VietnameseReviewSentimentModel
from app.reviews.service import ReviewService


USER = UserOut(id=10, email="student@example.com", name="Sinh viên", role="user")


class FakeRepo:
    def __init__(self, listing=None, duplicate=False):
        self.listing = listing or {"id": 7, "posted_by": None, "status": "active"}
        self.duplicate = duplicate
        self.created = []

    def get_listing(self, listing_id):
        return self.listing

    def create(
        self,
        listing_id,
        user_id,
        rating,
        comment,
        sentiment_label,
        negative_score,
        moderation_status,
        model_version,
    ):
        if self.duplicate:
            raise IntegrityError("insert", {}, Exception("unique"))
        self.created.append(
            {
                "listing_id": listing_id,
                "user_id": user_id,
                "rating": rating,
                "comment": comment,
                "sentiment_label": sentiment_label,
                "negative_score": negative_score,
                "moderation_status": moderation_status,
                "model_version": model_version,
            }
        )
        return ReviewOut(
            id=1,
            listing_id=listing_id,
            user_id=user_id,
            author_name="Sinh viên",
            rating=rating,
            comment=comment,
            sentiment_label=sentiment_label,
            negative_score=negative_score,
            is_flagged=moderation_status == "flagged",
            moderation_status=moderation_status,
            model_version=model_version,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )


def test_vietnamese_sentiment_flags_clear_negative_comment():
    prediction = VietnameseReviewSentimentModel().predict(
        "Phòng rất bẩn, chủ trọ thu phí vô lý và còn không trả tiền cọc"
    )

    assert prediction.label == "negative"
    assert prediction.is_flagged is True
    assert prediction.negative_score >= 0.62


def test_vietnamese_sentiment_keeps_positive_comment_published():
    prediction = VietnameseReviewSentimentModel().predict(
        "Phòng sạch sẽ, giá hợp lý và chủ nhà rất thân thiện"
    )

    assert prediction.label == "positive"
    assert prediction.is_flagged is False
    assert prediction.negative_score <= 0.38


def test_submit_review_persists_ai_flag_and_normalized_comment():
    repo = FakeRepo()
    service = ReviewService(repo, VietnameseReviewSentimentModel())

    result = service.submit(
        7,
        USER,
        ReviewCreate(
            rating=1,
            comment="  Phòng rất bẩn, chủ trọ thu phí vô lý và không trả tiền cọc.  ",
        ),
    )

    assert result.is_flagged is True
    assert repo.created[0]["moderation_status"] == "flagged"
    assert repo.created[0]["comment"] == "Phòng rất bẩn, chủ trọ thu phí vô lý và không trả tiền cọc."


def test_submit_review_rejects_owner_and_duplicate():
    owner_repo = FakeRepo(listing={"id": 7, "posted_by": USER.id, "status": "active"})
    with pytest.raises(HTTPException) as owner_error:
        ReviewService(owner_repo).submit(
            7,
            USER,
            ReviewCreate(rating=5, comment="Phòng của tôi rất tuyệt vời"),
        )
    assert owner_error.value.status_code == 400

    with pytest.raises(HTTPException) as duplicate_error:
        ReviewService(FakeRepo(duplicate=True)).submit(
            7,
            USER,
            ReviewCreate(rating=4, comment="Phòng khá tốt và đúng mô tả"),
        )
    assert duplicate_error.value.status_code == 409
