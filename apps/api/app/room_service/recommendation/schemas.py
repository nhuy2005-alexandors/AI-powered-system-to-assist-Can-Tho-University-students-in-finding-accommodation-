"""Validated recommendation inputs and public outputs."""
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class Preferences(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    needs: str = Field(min_length=1, max_length=1500)
    max_price: int = Field(gt=0, le=100_000_000)
    district: str | None = Field(default=None, min_length=1, max_length=100)


class PreviewRequest(Preferences):
    top_k: int = Field(default=10, ge=1, le=20)
    rerank: bool = False


class ProfileOut(BaseModel):
    preferences: Preferences
    embedding_model: str
    updated_at: datetime
    profile_version: int = 1
    behavior_listing_count: int = 0
    behavior_weight: float = 0.0
    behavior_blend: float = 0.0


class InteractionIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    listing_id: int = Field(gt=0)
    type: Literal["view", "save", "contact", "not_interested"]
    duration_ms: int | None = Field(default=None, ge=0, le=86_400_000)


class InteractionOut(BaseModel):
    event_id: str
    received_at: datetime
    profile_updated: bool = False
    learning_status: Literal["updated", "unchanged", "no_profile", "pending"] = "unchanged"
    event_learning_reason: Literal[
        "eligible",
        "duplicate_signal",
        "short_view",
        "excluded",
        "unavailable_embedding",
        "stale_generation",
        "no_profile",
        "pending",
    ] = "pending"
    profile_version: int | None = None
    behavior_listing_count: int = 0
    learning_warning: str | None = None


class RecommendationItem(BaseModel):
    listing_id: int
    title: str
    price: int
    area: float | None = None
    district: str | None = None
    housing_type: str | None = None
    offer_kind: str | None = None
    description_is_partial: bool | None = None
    source_contact_url: str | None = None
    source_url: str | None = None
    cosine_score: float
    cosine_rank: int
    rerank_score: float | None = None


class RecommendationsOut(BaseModel):
    preferences: Preferences
    items: list[RecommendationItem]
    eligible_count: int
    retrieved_count: int
    embedding_model: str
    reranker_model: str | None = None
    elapsed_ms: int
    warnings: list[str] = Field(default_factory=list)
