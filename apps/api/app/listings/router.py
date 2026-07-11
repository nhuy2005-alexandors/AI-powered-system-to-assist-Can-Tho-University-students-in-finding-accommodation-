import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.engine import Engine

from ..auth import get_current_user
from ..auth.schemas import UserOut
from ..config import settings
from ..crawler.geocode import Geocoder, haversine_m, CTU_LAT, CTU_LNG
from .repo import ListingQueryRepo, ListingWriteRepo
from .routing import CAMPUSES, matrix_minutes, route_geometry
from .schemas import ListingCreate, ListingOut, ListingUpdate, SearchParams, SearchResult, SortBy

log = logging.getLogger("listings.router")

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


def get_write_repo() -> ListingWriteRepo:
    if _engine is None:
        raise HTTPException(503, "Listings repo chưa khởi tạo")
    return ListingWriteRepo(_engine)


async def _geocode_address(address: str | None):
    """Geocode address → (lat, lng, conf, distance_to_ctu). None nếu không có address."""
    if not address:
        return None, None, None, None
    async with Geocoder() as g:
        lat, lng, conf = await g.geocode(address)
    dist = haversine_m(lat, lng, CTU_LAT, CTU_LNG) if lat is not None and lng is not None else None
    return lat, lng, conf, dist


async def _route_one(lat: float | None, lng: float | None) -> list[float] | None:
    """Route 1 điểm tới 3 campus (VIỆC 4 — re-route khi user sửa address).

    ors_api_key rỗng hoặc lỗi mạng → None, skip êm (không chặn create/update tin).
    """
    if lat is None or lng is None or not settings.ors_api_key:
        return None
    try:
        times = await matrix_minutes([(lat, lng)])
        return times[0] if times else None
    except Exception as exc:  # noqa: BLE001 — routing lỗi không chặn CRUD tin
        log.warning("route on address change fail: %s", exc)
        return None


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


@router.get("/mine", response_model=list[ListingOut])
def my_listings(
    user: UserOut = Depends(get_current_user),
    repo: ListingQueryRepo = Depends(get_repo),
):
    """Tin do user tự đăng ("Tin của tôi"). Phải khai báo TRƯỚC /{listing_id}."""
    return repo.by_owner(user.id)


@router.get("/{listing_id}", response_model=ListingOut)
def get_listing(listing_id: int, repo: ListingQueryRepo = Depends(get_repo)):
    """Chi tiết 1 tin (FR-2.6). Ẩn tin expired/hidden."""
    item = repo.get_visible(listing_id)
    if item is None:
        raise HTTPException(404, "Không tìm thấy tin")
    return item


@router.get("/{listing_id}/route", response_model=list[list[float]])
async def get_route_geometry(
    listing_id: int,
    campus: int = Query(1, ge=0, le=2),
    repo: ListingQueryRepo = Depends(get_repo),
):
    """Polyline route thật campus→tin (FR-M.8), fetch on-demand khi user click 1 tin.

    campus: 0=khu I, 1=khu II (mặc định), 2=khu III.
    """
    item = repo.get_visible(listing_id)
    if item is None or item.lat is None or item.lng is None:
        raise HTTPException(404, "Không tìm thấy tin hoặc tin chưa có toạ độ")
    if not settings.ors_api_key:
        raise HTTPException(503, "Routing chưa cấu hình (ORS_API_KEY)")
    try:
        return await route_geometry(CAMPUSES[campus], (item.lat, item.lng))
    except Exception as exc:  # noqa: BLE001 — lỗi ORS → 502, không lộ trace
        raise HTTPException(502, f"Không lấy được route: {exc}") from exc


def _check_owner(owner_row, user: UserOut) -> None:
    """404 nếu tin không tồn tại, 403 nếu không phải chủ tin và không phải admin (FR-3)."""
    if owner_row is None:
        raise HTTPException(404, "Không tìm thấy tin")
    if user.id != owner_row["posted_by"] and user.role != "admin":
        raise HTTPException(403, "Không có quyền sửa/xoá tin này")


@router.post("", response_model=ListingOut, status_code=201)
async def create_listing(
    body: ListingCreate,
    user: UserOut = Depends(get_current_user),
    repo: ListingQueryRepo = Depends(get_repo),
    write: ListingWriteRepo = Depends(get_write_repo),
):
    """Đăng tin UGC (FR-3.1)."""
    lat, lng, conf, dist = await _geocode_address(body.address)
    new_id = write.create(body.model_dump(), user.id, lat, lng, conf, dist)
    times = await _route_one(lat, lng)
    if times is not None:
        write.set_route_time(new_id, times)
    return repo.get(new_id)


@router.put("/{listing_id}", response_model=ListingOut)
async def update_listing(
    listing_id: int,
    body: ListingUpdate,
    user: UserOut = Depends(get_current_user),
    repo: ListingQueryRepo = Depends(get_repo),
    write: ListingWriteRepo = Depends(get_write_repo),
):
    """Sửa tin UGC — chỉ chủ tin hoặc admin (FR-3.2)."""
    owner_row = write.get_owner(listing_id)
    _check_owner(owner_row, user)

    fields = body.model_dump(exclude_unset=True)
    lat, lng, conf, dist = None, None, None, None
    if "address" in fields:
        lat, lng, conf, dist = await _geocode_address(fields["address"])

    write.update(listing_id, fields, lat, lng, conf, dist)
    if "address" in fields:
        times = await _route_one(lat, lng)
        if times is not None:
            write.set_route_time(listing_id, times)
    return repo.get(listing_id)


@router.delete("/{listing_id}", status_code=204)
def delete_listing(
    listing_id: int,
    user: UserOut = Depends(get_current_user),
    write: ListingWriteRepo = Depends(get_write_repo),
):
    """Xoá (ẩn) tin UGC — chỉ chủ tin hoặc admin (FR-3.3)."""
    owner_row = write.get_owner(listing_id)
    _check_owner(owner_row, user)
    write.soft_delete(listing_id)
