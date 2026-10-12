from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.engine import Engine

from .schemas import AdminReviewItem, ReviewList, ReviewOut, ReviewSummary


_PUBLIC_COLUMNS = (
    "r.id, r.listing_id, r.user_id, "
    "COALESCE(NULLIF(btrim(u.name), ''), split_part(u.email, '@', 1)) AS author_name, "
    "u.avatar_url AS author_avatar_url, r.rating, r.comment, r.sentiment_label, "
    "r.negative_score, (r.moderation_status = 'flagged') AS is_flagged, "
    "r.moderation_status, r.model_version, r.created_at, r.updated_at"
)


def _review_out(row) -> ReviewOut:
    return ReviewOut(**dict(row))


class ReviewRepository:
    def __init__(self, engine: Engine):
        self.engine = engine

    def get_listing(self, listing_id: int) -> dict | None:
        with self.engine.connect() as conn:
            row = conn.execute(
                text(
                    "SELECT id, posted_by, status::text AS status "
                    "FROM aggregated_listings WHERE id = :id"
                ),
                {"id": listing_id},
            ).mappings().first()
        return dict(row) if row else None

    def create(
        self,
        listing_id: int,
        user_id: int,
        rating: int,
        comment: str,
        sentiment_label: str,
        negative_score: float,
        moderation_status: str,
        model_version: str,
    ) -> ReviewOut:
        with self.engine.begin() as conn:
            review_id = conn.execute(
                text(
                    "INSERT INTO listing_reviews "
                    "(listing_id, user_id, rating, comment, sentiment_label, negative_score, "
                    "moderation_status, model_version) VALUES "
                    "(:listing_id, :user_id, :rating, :comment, :sentiment_label, :negative_score, "
                    ":moderation_status, :model_version) RETURNING id"
                ),
                {
                    "listing_id": listing_id,
                    "user_id": user_id,
                    "rating": rating,
                    "comment": comment,
                    "sentiment_label": sentiment_label,
                    "negative_score": negative_score,
                    "moderation_status": moderation_status,
                    "model_version": model_version,
                },
            ).scalar_one()
            row = conn.execute(
                text(
                    f"SELECT {_PUBLIC_COLUMNS} FROM listing_reviews r "
                    "JOIN users u ON u.id = r.user_id WHERE r.id = :id"
                ),
                {"id": review_id},
            ).mappings().one()
        return _review_out(row)

    def list_for_listing(self, listing_id: int, limit: int, offset: int) -> ReviewList:
        with self.engine.connect() as conn:
            aggregate = conn.execute(
                text(
                    "SELECT count(*) AS total, round(avg(rating)::numeric, 1) AS average_rating, "
                    "count(*) FILTER (WHERE rating = 1) AS rating_1, "
                    "count(*) FILTER (WHERE rating = 2) AS rating_2, "
                    "count(*) FILTER (WHERE rating = 3) AS rating_3, "
                    "count(*) FILTER (WHERE rating = 4) AS rating_4, "
                    "count(*) FILTER (WHERE rating = 5) AS rating_5 "
                    "FROM listing_reviews WHERE listing_id = :listing_id "
                    "AND moderation_status <> 'hidden'"
                ),
                {"listing_id": listing_id},
            ).mappings().one()
            rows = conn.execute(
                text(
                    f"SELECT {_PUBLIC_COLUMNS} FROM listing_reviews r "
                    "JOIN users u ON u.id = r.user_id "
                    "WHERE r.listing_id = :listing_id AND r.moderation_status <> 'hidden' "
                    "ORDER BY r.created_at DESC LIMIT :limit OFFSET :offset"
                ),
                {"listing_id": listing_id, "limit": limit, "offset": offset},
            ).mappings().all()

        summary = ReviewSummary(
            total=int(aggregate["total"]),
            average_rating=float(aggregate["average_rating"])
            if aggregate["average_rating"] is not None
            else None,
            rating_counts={
                rating: int(aggregate[f"rating_{rating}"]) for rating in range(1, 6)
            },
        )
        return ReviewList(summary=summary, items=[_review_out(row) for row in rows])

    def flagged(self, limit: int, offset: int) -> tuple[int, list[AdminReviewItem]]:
        with self.engine.connect() as conn:
            total = conn.execute(
                text("SELECT count(*) FROM listing_reviews WHERE moderation_status = 'flagged'")
            ).scalar_one()
            rows = conn.execute(
                text(
                    f"SELECT {_PUBLIC_COLUMNS}, l.title AS listing_title "
                    "FROM listing_reviews r JOIN users u ON u.id = r.user_id "
                    "JOIN aggregated_listings l ON l.id = r.listing_id "
                    "WHERE r.moderation_status = 'flagged' "
                    "ORDER BY r.created_at DESC LIMIT :limit OFFSET :offset"
                ),
                {"limit": limit, "offset": offset},
            ).mappings().all()
        return int(total), [AdminReviewItem(**dict(row)) for row in rows]

    def moderate(self, review_id: int, status: str) -> ReviewOut | None:
        with self.engine.begin() as conn:
            result = conn.execute(
                text(
                    "UPDATE listing_reviews SET moderation_status = :status, updated_at = now() "
                    "WHERE id = :id"
                ),
                {"id": review_id, "status": status},
            )
            if not result.rowcount:
                return None
            row = conn.execute(
                text(
                    f"SELECT {_PUBLIC_COLUMNS} FROM listing_reviews r "
                    "JOIN users u ON u.id = r.user_id WHERE r.id = :id"
                ),
                {"id": review_id},
            ).mappings().one()
        return _review_out(row)
