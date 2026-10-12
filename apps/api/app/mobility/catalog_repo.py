"""Read the mobility catalog only from the pinned handoff view."""
from sqlalchemy import Engine, text

from .contracts import BoundingBox, CatalogListing, CatalogPage, Position


PINNED_PACKAGE_ID = "ccd4bb988a93e6b676d2baa49de70d7e20a9b63c64a836bd673e514c95371d35"
PINNED_CATALOG_SHA256 = "b859bab1dc66808adc897f8f2b0b858d6aa2aa3954e52fc92c8e816e533b5947"
PINNED_CATALOG_SIZE = 789

_READY_SQL = text("""
    SELECT COUNT(*) AS total,
           COUNT(*) FILTER (
               WHERE package_id = :package_id
                 AND catalog_sha256 = :catalog_sha256
           ) AS pinned_total
    FROM public.catalog_handoff_v1
""")

_COUNT_SQL = """
    SELECT COUNT(*) AS total
    FROM public.catalog_handoff_v1 AS v
    WHERE v.package_id = :package_id
      AND v.catalog_sha256 = :catalog_sha256
      {bbox_filter}
"""

_LISTING_PROJECTION = """
    v.id, v.title, v.source, v.source_id, v.source_url, v.source_contact_url,
    v.price, v.area, v.address, v.district, v.description, v.images,
    v.housing_type, v.offer_kind, v.description_state, v.description_completeness,
    v.description_is_partial, v.unit_type_uncertain, v.offer_context_uncertain,
    v.mixed_use_possible, v.lease_transfer_terms_verified, v.parsed_amenities,
    ST_Y(v.geom) AS lat, ST_X(v.geom) AS lng
"""

_LISTING_SQL = text(f"""
    SELECT {_LISTING_PROJECTION}
    FROM public.catalog_handoff_v1 AS v
    WHERE v.id = :listing_id
      AND v.package_id = :package_id
      AND v.catalog_sha256 = :catalog_sha256
""")

_POSITION_SQL = text("""
    SELECT ST_Y(v.geom) AS lat, ST_X(v.geom) AS lng
    FROM public.catalog_handoff_v1 AS v
    WHERE v.id = :listing_id
      AND v.package_id = :package_id
      AND v.catalog_sha256 = :catalog_sha256
""")

_LIST_PAGE_SQL = text(f"""
    SELECT {_LISTING_PROJECTION}
    FROM public.catalog_handoff_v1 AS v
    WHERE v.package_id = :package_id
      AND v.catalog_sha256 = :catalog_sha256
      {{bbox_filter}}
    ORDER BY v.id
    LIMIT :limit OFFSET :offset
""")

_BBOX_FILTER = "AND v.geom && ST_MakeEnvelope(:west, :south, :east, :north, 4326)"
_PUBLIC_LISTING_FIELDS = (
    "id", "title", "source", "source_id", "source_url", "source_contact_url",
    "price", "area", "address", "district", "description", "images",
    "housing_type", "offer_kind", "description_state", "description_completeness",
    "description_is_partial", "unit_type_uncertain", "offer_context_uncertain",
    "mixed_use_possible", "lease_transfer_terms_verified", "parsed_amenities",
)


class CatalogUnavailable(RuntimeError):
    """The exact pinned catalog cannot be read safely."""


class CatalogRepo:
    """Read-only adapter for the versioned catalog handoff view."""

    def __init__(self, engine: Engine, package_id: str = PINNED_PACKAGE_ID):
        self.engine = engine
        self.package_id = package_id

    def list_page(self, page: int = 1, size: int = 50,
                  bbox: BoundingBox | None = None) -> CatalogPage:
        if page < 1 or size < 1 or size > 100:
            raise ValueError("page and size are outside the catalog bounds")

        params = self._pin_params()
        bbox_filter = ""
        if bbox is not None:
            bbox_filter = _BBOX_FILTER
            params.update({
                "south": bbox.south,
                "west": bbox.west,
                "north": bbox.north,
                "east": bbox.east,
            })

        try:
            with self.engine.connect() as connection:
                self._assert_ready(connection, params)
                count_sql = text(_COUNT_SQL.format(bbox_filter=bbox_filter))
                total_row = connection.execute(count_sql, params).mappings().one()
                total = int(total_row["total"])

                listing_params = params | {
                    "limit": size,
                    "offset": (page - 1) * size,
                }
                listing_sql = text(_LIST_PAGE_SQL.text.format(bbox_filter=bbox_filter))
                rows = connection.execute(listing_sql, listing_params).mappings().all()
                items = [self._listing_from_row(row) for row in rows]
                return CatalogPage(items=items, total=total, page=page, size=size)
        except CatalogUnavailable:
            raise
        except Exception:
            raise self._unavailable() from None

    def get_listing(self, listing_id: int) -> CatalogListing | None:
        params = self._pin_params() | {"listing_id": listing_id}
        try:
            with self.engine.connect() as connection:
                self._assert_ready(connection, params)
                row = connection.execute(_LISTING_SQL, params).mappings().first()
                return self._listing_from_row(row) if row is not None else None
        except CatalogUnavailable:
            raise
        except Exception:
            raise self._unavailable() from None

    def get_position(self, listing_id: int) -> Position | None:
        params = self._pin_params() | {"listing_id": listing_id}
        try:
            with self.engine.connect() as connection:
                self._assert_ready(connection, params)
                row = connection.execute(_POSITION_SQL, params).mappings().first()
                return self._position_from_row(row) if row is not None else None
        except CatalogUnavailable:
            raise
        except Exception:
            raise self._unavailable() from None

    def _pin_params(self) -> dict[str, str]:
        return {
            "package_id": self.package_id,
            "catalog_sha256": PINNED_CATALOG_SHA256,
        }

    @staticmethod
    def _assert_ready(connection, params: dict[str, str]) -> None:
        pin_params = {
            "package_id": params["package_id"],
            "catalog_sha256": params["catalog_sha256"],
        }
        result = connection.execute(_READY_SQL, pin_params).mappings().one()
        if (int(result["total"]) != PINNED_CATALOG_SIZE
                or int(result["pinned_total"]) != PINNED_CATALOG_SIZE):
            raise CatalogRepo._unavailable()

    @staticmethod
    def _position_from_row(row) -> Position | None:
        lat, lng = row.get("lat"), row.get("lng")
        if lat is None and lng is None:
            return None
        if lat is None or lng is None:
            raise ValueError("catalog position contains only one coordinate")
        # No precision or verification evidence is inferred from coordinate digits.
        return Position(lat=lat, lng=lng)

    @staticmethod
    def _listing_from_row(row) -> CatalogListing:
        payload = {field: row.get(field) for field in _PUBLIC_LISTING_FIELDS}
        if payload["images"] is None:
            payload["images"] = []
        payload["position"] = CatalogRepo._position_from_row(row)
        return CatalogListing.model_validate(payload)

    @staticmethod
    def _unavailable() -> CatalogUnavailable:
        return CatalogUnavailable("mobility catalog is unavailable")
