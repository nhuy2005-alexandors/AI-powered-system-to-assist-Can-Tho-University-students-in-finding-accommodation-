from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.engine import Engine

from .repo import ListingQueryRepo
from .schemas import ListingOut, SearchParams, SearchResult, SortBy

router = APIRouter(prefix="/listings", tags=["listings"])

# engine được set bởi main.py qua init_listings(engine)
_engine: Engine | None = None


def init_listings(engine: Engine) -> None:
    global _engine
    _engine = engine


def get_repo() -> ListingQueryRepo:
    if _engine is None:
        raise HTTPException(503, "Listings repo chưa khởi tạo")
    return ListingQueryRepo(_engine)


@router.get("", response_model=SearchResult)
def search_listings(
    q: str | None = None,
    min_price: int | None = None,
    max_price: int | None = None,
    min_area: float | None = None,
    district: str | None = None,
    amenities: list[str] = Query(default_factory=list),
    max_distance_ctu: float | None = None,
    sort: SortBy = SortBy.newest,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    repo: ListingQueryRepo = Depends(get_repo),
):
    """Tìm kiếm + lọc + sắp xếp + phân trang (FR-2.1/2.2/2.3). Ẩn tin expired."""
    params = SearchParams(
        q=q, min_price=min_price, max_price=max_price, min_area=min_area,
        district=district, amenities=amenities, max_distance_ctu=max_distance_ctu,
        sort=sort, page=page, size=size,
    )
    total, items = repo.search(params)
    return SearchResult(total=total, page=page, size=size, items=items)


@router.get("/nearby", response_model=list[ListingOut])
def nearby_listings(
    lat: float,
    lng: float,
    radius: float = Query(2000, gt=0, le=20000),
    repo: ListingQueryRepo = Depends(get_repo),
):
    """Tìm theo bán kính trên bản đồ (FR-2.5). radius: mét."""
    return repo.nearby(lat, lng, radius)


@router.get("/{listing_id}", response_model=ListingOut)
def get_listing(listing_id: int, repo: ListingQueryRepo = Depends(get_repo)):
    """Chi tiết 1 tin (FR-2.6)."""
    item = repo.get(listing_id)
    if item is None:
        raise HTTPException(404, "Không tìm thấy tin")
    return item
