from sqlalchemy import text
from sqlalchemy.engine import Engine

from .schemas import (
    ListingOut,
    SearchParams,
    SortBy,
    freshness_label,
    risk_level,
)

# cột select chung; geom → tách lat/lng qua ST_X/ST_Y
_COLS = (
    "id, title, price, area, address, district, "
    "ST_Y(geom) AS lat, ST_X(geom) AS lng, distance_to_ctu, images, "
    "source, source_url, risk_score, geocode_confidence, freshness_score, last_seen"
)

_SORT_SQL = {
    SortBy.price_asc: "price ASC NULLS LAST",
    SortBy.price_desc: "price DESC NULLS LAST",
    SortBy.newest: "last_seen DESC",
    SortBy.nearest: "distance_to_ctu ASC NULLS LAST",
    SortBy.freshness: "freshness_score DESC",
}


def build_filters(p: SearchParams) -> tuple[str, dict]:
    """Dựng mệnh đề WHERE + params. Tách riêng để unit-test không cần DB.

    Luôn ẩn tin status='expired' (FR-2.8) và 'hidden' (user tự ẩn).
    """
    clauses = ["status NOT IN ('expired', 'hidden')"]
    params: dict = {}

    if p.q:
        clauses.append("(title ILIKE :q OR description ILIKE :q OR address ILIKE :q)")
        params["q"] = f"%{p.q}%"
    if p.min_price is not None:
        clauses.append("price >= :min_price")
        params["min_price"] = p.min_price
    if p.max_price is not None:
        clauses.append("price <= :max_price")
        params["max_price"] = p.max_price
    if p.min_area is not None:
        clauses.append("area >= :min_area")
        params["min_area"] = p.min_area
    if p.district:
        clauses.append("district ILIKE :district")
        params["district"] = f"%{p.district}%"
    if p.max_distance_ctu is not None:
        clauses.append("distance_to_ctu <= :max_dist")
        params["max_dist"] = p.max_distance_ctu
    # amenities: JSONB chứa key = true
    for i, am in enumerate(p.amenities):
        key = f"am{i}"
        clauses.append(f"(parsed_amenities ->> :{key})::boolean IS TRUE")
        params[key] = am

    return " AND ".join(clauses), params


def _to_out(row) -> ListingOut:
    d = dict(row)
    d["images"] = d.get("images") or []
    d["risk_level"] = risk_level(d.get("risk_score"))
    d["freshness_label"] = freshness_label(d.get("last_seen"))
    return ListingOut(**d)


class ListingQueryRepo:
    """Đọc listings phục vụ search/detail/nearby (FR-2)."""

    def __init__(self, engine: Engine):
        self.engine = engine

    def search(self, p: SearchParams) -> tuple[int, list[ListingOut]]:
        where, params = build_filters(p)
        order = _SORT_SQL[p.sort]
        offset = (p.page - 1) * p.size

        with self.engine.connect() as conn:
            total = conn.execute(
                text(f"SELECT count(*) FROM aggregated_listings WHERE {where}"), params
            ).scalar_one()
            rows = conn.execute(
                text(
                    f"SELECT {_COLS} FROM aggregated_listings WHERE {where} "
                    f"ORDER BY {order} LIMIT :limit OFFSET :offset"
                ),
                {**params, "limit": p.size, "offset": offset},
            ).mappings().all()
        return total, [_to_out(r) for r in rows]

    def get(self, listing_id: int) -> ListingOut | None:
        with self.engine.connect() as conn:
            row = conn.execute(
                text(f"SELECT {_COLS} FROM aggregated_listings WHERE id = :id"),
                {"id": listing_id},
            ).mappings().first()
        return _to_out(row) if row else None

    def get_visible(self, listing_id: int) -> ListingOut | None:
        """Detail công khai — ẩn tin expired/hidden (dùng cho GET /listings/{id})."""
        with self.engine.connect() as conn:
            row = conn.execute(
                text(
                    f"SELECT {_COLS} FROM aggregated_listings "
                    "WHERE id = :id AND status NOT IN ('expired', 'hidden')"
                ),
                {"id": listing_id},
            ).mappings().first()
        return _to_out(row) if row else None

    def nearby(self, lat: float, lng: float, radius_m: float, limit: int = 50) -> list[ListingOut]:
        """Tin trong bán kính (FR-2.5) — PostGIS ST_DWithin trên geography."""
        with self.engine.connect() as conn:
            rows = conn.execute(
                text(
                    f"SELECT {_COLS}, "
                    "ST_Distance(geom::geography, ST_SetSRID(ST_MakePoint(:lng,:lat),4326)::geography) AS dist "
                    "FROM aggregated_listings "
                    "WHERE status NOT IN ('expired', 'hidden') AND geom IS NOT NULL "
                    "AND ST_DWithin(geom::geography, ST_SetSRID(ST_MakePoint(:lng,:lat),4326)::geography, :r) "
                    "ORDER BY dist ASC LIMIT :limit"
                ),
                {"lat": lat, "lng": lng, "r": radius_m, "limit": limit},
            ).mappings().all()
        return [_to_out(r) for r in rows]


# cột được phép sửa qua PUT (partial update) — khớp field của ListingUpdate
_UPDATABLE_COLS = ("title", "price", "area", "address", "district", "description", "images")

_INSERT_UGC = text(
    """
    INSERT INTO aggregated_listings
        (title, price, area, address, district, images, description,
         source, source_url, source_id, posted_by,
         geom, distance_to_ctu, geocode_confidence,
         status, first_seen, last_seen, updated_at)
    VALUES
        (:title, :price, :area, :address, :district, :images, :description,
         'user', NULL, NULL, :posted_by,
         CASE WHEN CAST(:lat AS DOUBLE PRECISION) IS NULL THEN NULL
              ELSE ST_SetSRID(ST_MakePoint(CAST(:lng AS DOUBLE PRECISION), CAST(:lat AS DOUBLE PRECISION)), 4326) END,
         CAST(:distance_to_ctu AS REAL), :geocode_confidence,
         'active', now(), now(), now())
    RETURNING id
    """
)


class ListingWriteRepo:
    """Ghi listings UGC (đăng/sửa/xoá tin của user) — tách khỏi ListingQueryRepo (chỉ đọc)."""

    def __init__(self, engine: Engine):
        self.engine = engine

    def create(self, data: dict, user_id: int, lat, lng, conf, dist) -> int:
        with self.engine.begin() as conn:
            new_id = conn.execute(
                _INSERT_UGC,
                {
                    "title": data["title"],
                    "price": data.get("price"),
                    "area": data.get("area"),
                    "address": data.get("address"),
                    "district": data.get("district"),
                    "images": data.get("images") or [],
                    "description": data.get("description"),
                    "posted_by": user_id,
                    "lat": lat,
                    "lng": lng,
                    "distance_to_ctu": dist,
                    "geocode_confidence": conf,
                },
            ).scalar_one()
        return new_id

    def get_owner(self, listing_id: int):
        """Trả row {posted_by, status} hoặc None nếu id không tồn tại (dùng cho check 404/403)."""
        with self.engine.connect() as conn:
            row = conn.execute(
                text("SELECT posted_by, status FROM aggregated_listings WHERE id = :id"),
                {"id": listing_id},
            ).mappings().first()
        return row

    def update(self, listing_id: int, fields: dict, lat, lng, conf, dist) -> None:
        """Update partial — chỉ set cột có trong fields (khoá đã whitelist qua ListingUpdate)."""
        set_clauses = [f"{col} = :{col}" for col in fields if col in _UPDATABLE_COLS]
        params: dict = {**fields, "id": listing_id}

        if "address" in fields and lat is not None and lng is not None:
            set_clauses.append(
                "geom = ST_SetSRID(ST_MakePoint(CAST(:lng AS DOUBLE PRECISION), "
                "CAST(:lat AS DOUBLE PRECISION)), 4326)"
            )
            set_clauses.append("distance_to_ctu = CAST(:distance_to_ctu AS REAL)")
            set_clauses.append("geocode_confidence = :geocode_confidence")
            params["lat"] = lat
            params["lng"] = lng
            params["distance_to_ctu"] = dist
            params["geocode_confidence"] = conf

        if not set_clauses:
            return

        set_clauses.append("updated_at = now()")
        sql = f"UPDATE aggregated_listings SET {', '.join(set_clauses)} WHERE id = :id"
        with self.engine.begin() as conn:
            conn.execute(text(sql), params)

    def soft_delete(self, listing_id: int) -> None:
        """Ẩn tin (status='hidden') thay vì xoá cứng — user có thể khôi phục sau (không làm ở đây)."""
        with self.engine.begin() as conn:
            conn.execute(
                text(
                    "UPDATE aggregated_listings SET status = 'hidden', updated_at = now() "
                    "WHERE id = :id"
                ),
                {"id": listing_id},
            )
