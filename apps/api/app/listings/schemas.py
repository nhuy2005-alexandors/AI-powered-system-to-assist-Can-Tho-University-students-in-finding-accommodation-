from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class SortBy(str, Enum):
    price_asc = "price_asc"
    price_desc = "price_desc"
    newest = "newest"
    nearest = "nearest"
    freshness = "freshness"


def risk_level(score: float | None) -> str:
    """risk_score → nhãn badge (FR-7.2). ✅ safe / ⚠️ caution / 🔴 suspicious."""
    if score is None:
        return "unknown"
    if score < 0.3:
        return "safe"
    if score < 0.6:
        return "caution"
    return "suspicious"


def freshness_label(last_seen: datetime | None, now: datetime | None = None) -> str:
    """last_seen → 'cập nhật X giờ/ngày trước' (FR-2.8)."""
    if last_seen is None:
        return "không rõ"
    from datetime import timezone

    now = now or datetime.now(timezone.utc)
    if last_seen.tzinfo is None:
        last_seen = last_seen.replace(tzinfo=timezone.utc)
    secs = max(0, (now - last_seen).total_seconds())
    if secs < 3600:
        return f"cập nhật {int(secs // 60)} phút trước"
    if secs < 86400:
        return f"cập nhật {int(secs // 3600)} giờ trước"
    return f"cập nhật {int(secs // 86400)} ngày trước"


class SearchParams(BaseModel):
    q: str | None = None
    min_price: int | None = None
    max_price: int | None = None
    min_area: float | None = None
    district: str | None = None
    amenities: list[str] = Field(default_factory=list)
    max_distance_ctu: float | None = None        # mét
    sort: SortBy = SortBy.newest
    page: int = Field(default=1, ge=1)
    size: int = Field(default=20, ge=1, le=100)


class ListingOut(BaseModel):
    id: int
    title: str
    price: int | None = None
    area: float | None = None
    address: str | None = None
    district: str | None = None
    lat: float | None = None
    lng: float | None = None
    distance_to_ctu: float | None = None
    images: list[str] = Field(default_factory=list)
    source: str
    source_url: str | None = None
    risk_score: float | None = None
    risk_level: str = "unknown"
    geocode_confidence: str | None = None
    freshness_score: float | None = None
    freshness_label: str = ""
    last_seen: datetime | None = None


class SearchResult(BaseModel):
    total: int
    page: int
    size: int
    items: list[ListingOut]


class ListingCreate(BaseModel):
    """Payload đăng tin UGC (FR-3.1)."""

    title: str = Field(min_length=1)
    price: int | None = None
    area: float | None = None
    address: str | None = None
    district: str | None = None
    description: str | None = None
    images: list[str] = Field(default_factory=list)


class ListingUpdate(BaseModel):
    """Payload sửa tin UGC — mọi field optional (partial update)."""

    title: str | None = None
    price: int | None = None
    area: float | None = None
    address: str | None = None
    district: str | None = None
    description: str | None = None
    images: list[str] | None = None
