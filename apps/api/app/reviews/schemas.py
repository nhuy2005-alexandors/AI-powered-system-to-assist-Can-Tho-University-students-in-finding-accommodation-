from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class SentimentLabel(str, Enum):
    positive = "positive"
    neutral = "neutral"
    negative = "negative"


class ModerationStatus(str, Enum):
    published = "published"
    flagged = "flagged"
    hidden = "hidden"


class ReviewCreate(BaseModel):
    rating: int = Field(ge=1, le=5)
    comment: str = Field(min_length=10, max_length=2000)


class ReviewOut(BaseModel):
    id: int
    listing_id: int
    user_id: int
    author_name: str
    author_avatar_url: str | None = None
    rating: int
    comment: str
    sentiment_label: SentimentLabel
    negative_score: float
    is_flagged: bool
    moderation_status: ModerationStatus
    model_version: str
    created_at: datetime
    updated_at: datetime


class ReviewSummary(BaseModel):
    average_rating: float | None = None
    total: int = 0
    rating_counts: dict[int, int] = Field(default_factory=dict)


class ReviewList(BaseModel):
    summary: ReviewSummary
    items: list[ReviewOut]


class ReviewModerationAction(str, Enum):
    approve = "approve"
    hide = "hide"


class ReviewModerationIn(BaseModel):
    action: ReviewModerationAction


class AdminReviewItem(ReviewOut):
    listing_title: str


class AdminReviewList(BaseModel):
    total: int
    items: list[AdminReviewItem]
