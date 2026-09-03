from datetime import datetime, timezone
import json

from sqlalchemy import text
from sqlalchemy.engine import Engine

from .schemas import NormalizedListing

# Upsert: match theo (source, source_id). content_hash đổi → cập nhật field + updated_at.
_UPSERT = text(
    """
    INSERT INTO aggregated_listings
        (title, price, area, address, district, images, description,
         source, source_url, source_id, content_hash, parsed_amenities,
         geom, distance_to_ctu, geocode_confidence,
         status, first_seen, last_seen, miss_count, freshness_score, updated_at)
    VALUES
        (:title, :price, :area, :address, :district, :images, :description,
         :source, :source_url, :source_id, :content_hash, CAST(:amenities AS JSONB),
         CASE WHEN CAST(:lat AS DOUBLE PRECISION) IS NULL THEN NULL
              ELSE ST_SetSRID(ST_MakePoint(CAST(:lng AS DOUBLE PRECISION), CAST(:lat AS DOUBLE PRECISION)), 4326) END,
         CAST(:distance_to_ctu AS REAL), :geocode_confidence,
         'active', :now, :now, 0, 1.0, :now)
    ON CONFLICT (source, source_id) DO UPDATE SET
        last_seen = :now,
        miss_count = 0,
        freshness_score = 1.0,
        status = CASE WHEN aggregated_listings.status = 'expired'
                      THEN 'active' ELSE aggregated_listings.status END,
        title = CASE WHEN aggregated_listings.content_hash <> :content_hash
                     THEN :title ELSE aggregated_listings.title END,
        price = CASE WHEN aggregated_listings.content_hash <> :content_hash
                     THEN :price ELSE aggregated_listings.price END,
        area = CASE WHEN aggregated_listings.content_hash <> :content_hash
                    THEN :area ELSE aggregated_listings.area END,
        district = COALESCE(:district, aggregated_listings.district),
        description = CASE WHEN aggregated_listings.content_hash <> :content_hash
                          THEN :description ELSE aggregated_listings.description END,
        address = CASE WHEN aggregated_listings.content_hash <> :content_hash
                       THEN :address ELSE aggregated_listings.address END,
        images = CASE WHEN aggregated_listings.content_hash <> :content_hash
                      THEN :images ELSE aggregated_listings.images END,
        geom = CASE WHEN CAST(:lat AS DOUBLE PRECISION) IS NULL THEN aggregated_listings.geom
                    ELSE ST_SetSRID(ST_MakePoint(CAST(:lng AS DOUBLE PRECISION), CAST(:lat AS DOUBLE PRECISION)), 4326) END,
        distance_to_ctu = COALESCE(CAST(:distance_to_ctu AS REAL), aggregated_listings.distance_to_ctu),
        geocode_confidence = :geocode_confidence,
        content_hash = :content_hash,
        cleaning_status = CASE WHEN aggregated_listings.content_hash <> :content_hash
                               THEN 'raw' ELSE aggregated_listings.cleaning_status END,
        updated_at = CASE WHEN aggregated_listings.content_hash <> :content_hash
                          THEN :now ELSE aggregated_listings.updated_at END
    RETURNING (xmax = 0) AS inserted,
              (content_hash = :content_hash AND xmax <> 0) AS updated
    """
)


class ListingRepo:
    """DB I/O cho listings + crawl_runs. Tách khỏi pipeline để pipeline test được."""

    def __init__(self, engine: Engine):
        self.engine = engine

    def upsert(self, n: NormalizedListing) -> str:
        """Trả 'new' | 'updated' | 'seen'."""
        import json

        now = datetime.now(timezone.utc)
        with self.engine.begin() as conn:
            row = conn.execute(
                _UPSERT,
                {
                    "title": n.title,
                    "price": n.price,
                    "area": n.area,
                    "address": n.address,
                    "district": n.district,
                    "images": n.images,
                    "description": n.description,
                    "source": n.source,
                    "source_url": n.source_url,
                    "source_id": n.source_id,
                    "content_hash": n.content_hash,
                    "amenities": json.dumps(n.amenities),
                    "lat": n.lat,
                    "lng": n.lng,
                    "distance_to_ctu": n.distance_to_ctu,
                    "geocode_confidence": n.geocode_confidence,
                    "now": now,
                },
            ).one()
        if row.inserted:
            return "new"
        return "updated" if row.updated else "seen"

    def mark_misses(self, source: str, seen_ids: list[str]) -> int:
        """Sau full run: tin của nguồn không nằm trong seen_ids → miss_count++ và có thể expired."""
        with self.engine.begin() as conn:
            rows = conn.execute(
                text(
                    """
                    UPDATE aggregated_listings
                    SET miss_count = miss_count + 1,
                        status = CASE
                            WHEN status = 'flagged' THEN status
                            WHEN miss_count + 1 >= 2 THEN 'expired'::listing_status
                            ELSE status END
                    WHERE source = :source
                      AND (source_id IS NULL OR source_id <> ALL(:ids))
                      AND status <> 'expired'
                    RETURNING status
                    """
                ),
                {"source": source, "ids": seen_ids or [""]},
            ).fetchall()
        return sum(1 for r in rows if r.status == "expired")

    def pending_route(self) -> list[dict]:
        """Tin có geom nhưng chưa route_time_campus (mới crawl, hoặc backfill sót)."""
        with self.engine.connect() as conn:
            rows = conn.execute(
                text(
                    "SELECT id, ST_Y(geom) AS lat, ST_X(geom) AS lng "
                    "FROM aggregated_listings "
                    "WHERE geom IS NOT NULL AND route_time_campus IS NULL"
                )
            ).mappings().all()
        return [dict(r) for r in rows]

    def set_route_times(self, updates: list[tuple[int, list[float]]]) -> None:
        """Batch UPDATE route_time_campus. updates = [(listing_id, [khuI,II,III]), ...]."""
        if not updates:
            return
        with self.engine.begin() as conn:
            for listing_id, times in updates:
                conn.execute(
                    text("UPDATE aggregated_listings SET route_time_campus = :t WHERE id = :id"),
                    {"t": times, "id": listing_id},
                )

    def refresh_scores(self) -> None:
        """Tính lại freshness_score theo tuổi last_seen (gọi định kỳ)."""
        with self.engine.begin() as conn:
            conn.execute(
                text(
                    "UPDATE aggregated_listings "
                    "SET freshness_score = EXP(-EXTRACT(EPOCH FROM (now() - last_seen)) / 86400.0 / 7.0) "
                    "WHERE status <> 'expired'"
                )
            )

    def start_run(self, source: str, mode: str) -> int:
        with self.engine.begin() as conn:
            return conn.execute(
                text(
                    "INSERT INTO crawl_runs (source, mode) VALUES (:s, :m) RETURNING id"
                ),
                {"s": source, "m": mode},
            ).scalar_one()

    def finish_run(self, run_id: int, **counts) -> None:
        with self.engine.begin() as conn:
            conn.execute(
                text(
                    "UPDATE crawl_runs SET finished_at = now(), fetched = :fetched, "
                    "new_count = :new_count, updated_count = :updated_count, "
                    "expired_count = :expired_count, error = :error WHERE id = :id"
                ),
                {"id": run_id, **counts},
            )

    def latest_runs(self, limit: int = 10) -> list[dict]:
        with self.engine.connect() as conn:
            rows = conn.execute(
                text(
                    "SELECT source, mode, started_at, finished_at, fetched, "
                    "new_count, updated_count, expired_count, error "
                    "FROM crawl_runs ORDER BY started_at DESC LIMIT :n"
                ),
                {"n": limit},
            ).mappings().all()
        return [dict(r) for r in rows]
