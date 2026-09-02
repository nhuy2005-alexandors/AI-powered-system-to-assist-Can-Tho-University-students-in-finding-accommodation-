from typing import Any

from pydantic import BaseModel, Field, model_validator


class ChatFilters(BaseModel):
    min_price: int | None = Field(default=None, ge=0)
    max_price: int | None = Field(default=None, ge=0)
    min_area: float | None = Field(default=None, ge=0)
    district: str | None = None
    amenities: list[str] = Field(default_factory=list)
    gender: str | None = None
    max_distance_ctu: float | None = Field(default=None, ge=0)
    max_route_minutes: float | None = Field(default=None, ge=0)
    listing_type: str | None = None

    @model_validator(mode="after")
    def validate_price_range(self):
        if (
            self.min_price is not None
            and self.max_price is not None
            and self.min_price > self.max_price
        ):
            raise ValueError("min_price không được lớn hơn max_price")
        return self


class ChatAskRequest(BaseModel):
    """Stateless request: the API never receives or persists a chat identity."""

    message: str = Field(min_length=2, max_length=2000)
    filters: ChatFilters | None = None


class ChatListing(BaseModel):
    id: int
    title: str
    price: int | None = None
    area: float | None = None
    address: str | None = None
    district: str | None = None
    amenities: dict[str, Any] = Field(default_factory=dict)
    distance_to_ctu: float | None = None
    route_time_campus: list[float] | None = None
    source: str
    source_url: str | None = None
    similarity_score: float = 0.0
    vector_score: float = 0.0
    bm25_score: float = 0.0
    rank: int = 0
    match_reasons: list[str] = Field(default_factory=list)


class ChatSource(BaseModel):
    listing_id: int
    rank: int
    similarity_score: float
    title: str
    source: str
    source_url: str | None = None


class ChatAskResponse(BaseModel):
    answer: str
    intent: str
    confidence: float
    listings: list[ChatListing] = Field(default_factory=list, max_length=5)
    sources: list[ChatSource] = Field(default_factory=list, max_length=5)
    no_answer: bool = False
    degraded: bool = False
    degraded_reasons: list[str] = Field(default_factory=list)
    retrieval_mode: str = "hybrid"
    generation_provider: str = "template"
    generation_model: str | None = None
    latency_ms: int
