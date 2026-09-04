from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.engine import Engine

from .scoring import MODEL_VERSION, ScoreResult


class RiskRepository:
    def __init__(self, engine: Engine):
        self.engine = engine

    def get_listing(self, listing_id: int) -> dict | None:
        with self.engine.connect() as conn:
            row = conn.execute(
                text(
                    "SELECT id, title, description, price, area, address, district, images, "
                    "source, source_url, listing_type, quality_score, freshness_score, "
                    "geocode_confidence, risk_score, risk_reasons, risk_model, risk_evaluated_at, "
                    "(SELECT count(*) FROM reports r WHERE r.listing_id = aggregated_listings.id "
                    "AND r.status IN ('pending', 'reviewed')) AS report_count, "
                    "(SELECT count(*) FROM reports r WHERE r.listing_id = aggregated_listings.id "
                    "AND r.status IN ('pending', 'reviewed') AND r.reason = 'scam') AS scam_report_count "
                    "FROM aggregated_listings WHERE id = :id"
                ),
                {"id": listing_id},
            ).mappings().first()
        return dict(row) if row else None

    def district_median_price(self, listing: dict) -> float | None:
        district = listing.get("district")
        if not district:
            return None
        with self.engine.connect() as conn:
            value = conn.execute(
                text(
                    "SELECT percentile_cont(0.5) WITHIN GROUP (ORDER BY price) "
                    "FROM aggregated_listings WHERE status = 'active' "
                    "AND cleaning_status = 'cleaned' AND price IS NOT NULL "
                    "AND district = :district "
                    "AND listing_type = CAST(:listing_type AS listing_type_enum)"
                ),
                {
                    "district": district,
                    "listing_type": listing.get("listing_type") or "phong_tro",
                },
            ).scalar()
        return float(value) if value is not None else None

    def save(self, listing_id: int, result: ScoreResult) -> None:
        with self.engine.begin() as conn:
            conn.execute(
                text(
                    "UPDATE aggregated_listings SET risk_score = :score, "
                    "risk_reasons = :reasons, risk_model = :model, "
                    "risk_evaluated_at = :evaluated_at WHERE id = :id"
                ),
                {
                    "id": listing_id,
                    "score": result.score,
                    "reasons": result.reasons,
                    "model": MODEL_VERSION,
                    "evaluated_at": result.evaluated_at,
                },
            )

    def pending_ids(self, limit: int) -> list[int]:
        with self.engine.connect() as conn:
            rows = conn.execute(
                text(
                    "SELECT id FROM aggregated_listings WHERE status = 'active' "
                    "AND cleaning_status = 'cleaned' "
                    "AND (risk_evaluated_at IS NULL OR updated_at > risk_evaluated_at) "
                    "ORDER BY updated_at DESC LIMIT :limit"
                ),
                {"limit": limit},
            ).all()
        return [int(row[0]) for row in rows]
