"""PostgreSQL listing retrieval and optional MongoDB profile/event storage."""
import json
from datetime import datetime, timedelta, timezone
from threading import Lock
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import text


class ListingRepository:
    def __init__(self, engine):
        self.engine = engine

    def exists(self, listing_id: int) -> bool:
        with self.engine.connect() as conn:
            return (
                conn.execute(
                    text("SELECT 1 FROM aggregated_listings WHERE id=:id"),
                    {"id": listing_id},
                ).scalar()
                is not None
            )

    def embeddings(self, listing_ids: list[int], model: str) -> dict[int, list[float]]:
        if not listing_ids:
            return {}
        with self.engine.connect() as conn:
            rows = conn.execute(
                text("""
                SELECT id, embedding_vector::text AS vector
                FROM aggregated_listings
                WHERE id = ANY(:ids) AND status = 'active'
                  AND embedding_model = :model AND embedding_vector IS NOT NULL
                """),
                {"ids": listing_ids, "model": model},
            ).mappings()
            return {row["id"]: json.loads(row["vector"]) for row in rows}

    def search(
        self, vector: list[float], preferences, model: str, limit: int, excluded: list[int]
    ) -> list[dict]:
        params = {
            "vector": "[" + ",".join(str(v) for v in vector) + "]",
            "model": model,
            "price": preferences.max_price,
            "limit": limit,
        }
        clauses = [
            "l.status='active'",
            "l.price > 0",
            "l.price <= :price",
            "l.embedding_vector IS NOT NULL",
            "l.embedding_model=:model",
        ]
        if preferences.district:
            clauses.append("l.district=:district")
            params["district"] = preferences.district
        if excluded:
            clauses.append("NOT (l.id = ANY(:excluded))")
            params["excluded"] = excluded
        with self.engine.connect() as conn:
            conn.execute(text("SET TRANSACTION READ ONLY"))
            handoff = conn.execute(
                text("SELECT to_regclass('public.catalog_handoff_v1') IS NOT NULL")
            ).scalar()
            extra = (
                "c.housing_type, c.offer_kind, c.description_state, "
                "c.description_is_partial, c.source_contact_url"
                if handoff
                else "NULL::text AS housing_type, NULL::text AS offer_kind, "
                "NULL::text AS description_state, "
                "NULL::boolean AS description_is_partial, "
                "l.source_url AS source_contact_url"
            )
            join = "JOIN catalog_handoff_v1 c ON c.id=l.id" if handoff else ""
            sql = f"""
                WITH candidates AS MATERIALIZED (
                    SELECT l.id, l.title, l.price, l.area, l.district, l.address,
                           l.description, l.parsed_amenities, l.source_url,
                           l.embedding_vector, {extra}
                    FROM aggregated_listings l {join}
                    WHERE {" AND ".join(clauses)}
                )
                SELECT *, 1 - (embedding_vector <=> CAST(:vector AS vector)) AS cosine_score,
                       count(*) OVER () AS eligible_count
                FROM candidates ORDER BY cosine_score DESC, id ASC LIMIT :limit
            """
            return [dict(row) for row in conn.execute(text(sql), params).mappings()]


class ProfileRepository:
    def __init__(self, uri: str, database: str):
        self.uri = uri
        self.database = database
        self.client = None
        self.lock = Lock()

    @staticmethod
    def execute(operation):
        try:
            return operation()
        except HTTPException:
            raise
        except Exception:
            raise HTTPException(
                503, "Không đọc/ghi được dữ liệu recommendation trong MongoDB"
            ) from None

    def db(self):
        if not self.uri:
            raise HTTPException(503, "Chưa cấu hình RECOMMENDATION_MONGO_URI")
        with self.lock:
            if self.client is None:
                try:
                    from pymongo import MongoClient
                except ImportError:
                    raise HTTPException(503, "Cần cài requirements-recommendation.txt") from None
                client = MongoClient(
                    self.uri,
                    serverSelectionTimeoutMS=5000,
                    timeoutMS=10000,
                    tz_aware=True,
                )
                try:
                    db = client[self.database]
                    db.recommendation_profiles.create_index("user_id", unique=True)
                    db.recommendation_interactions.create_index(
                        [("user_id", 1), ("received_at", -1)]
                    )
                    db.recommendation_interactions.create_index(
                        [("user_id", 1), ("listing_id", 1), ("type", 1)]
                    )
                except Exception:
                    client.close()
                    raise HTTPException(
                        503, "Không kết nối/khởi tạo được MongoDB recommendation"
                    ) from None
                self.client = client
            return self.client[self.database]

    def get(self, user_id):
        return self.execute(
            lambda: self.db().recommendation_profiles.find_one({"user_id": user_id})
        )

    def save(self, user_id, preferences, vector, model):
        db = self.db()  # Check the optional driver before importing ReturnDocument.
        from pymongo import ReturnDocument

        now = datetime.now(timezone.utc)
        document = {
            "preferences": preferences.model_dump(),
            "initial_vector": vector,
            "preference_vector": vector,
            "embedding_model": model,
            "profile_generation": str(uuid4()),
            "behavior_since": now,
            "behavior_listing_count": 0,
            "behavior_weight": 0.0,
            "behavior_blend": 0.0,
            "behavior_signal_weights": {},
            "updated_at": now,
        }
        return self.execute(
            lambda: db.recommendation_profiles.find_one_and_update(
                {"user_id": user_id},
                {
                    "$set": document,
                    "$inc": {"profile_version": 1},
                    "$setOnInsert": {"created_at": now},
                },
                upsert=True,
                return_document=ReturnDocument.AFTER,
            )
        )

    def record(self, user_id, event, profile_generation=None):
        now = datetime.now(timezone.utc)
        document = {
            "user_id": user_id,
            **event.model_dump(),
            "received_at": now,
            "profile_generation": profile_generation,
        }
        result = self.execute(
            lambda: self.db().recommendation_interactions.insert_one(document)
        )
        return {"event_id": str(result.inserted_id), "received_at": now}

    def recent_signals(self, user_id, since, profile_generation):
        from .behavior import MIN_VIEW_DURATION_MS

        cutoff = datetime.now(timezone.utc) - timedelta(days=30)
        if since is not None:
            if since.tzinfo is None:
                since = since.replace(tzinfo=timezone.utc)
            cutoff = max(cutoff, since)
        # Limit distinct listings so repeated events do not consume extra slots.
        pipeline = [
            {
                "$match": {
                    "user_id": user_id,
                    "profile_generation": profile_generation,
                    "received_at": {"$gte": cutoff},
                    "$or": [
                        {"type": {"$in": ["save", "contact"]}},
                        {
                            "type": "view",
                            "duration_ms": {"$gte": MIN_VIEW_DURATION_MS},
                        },
                    ],
                }
            },
            {
                "$group": {
                    "_id": "$listing_id",
                    "types": {"$addToSet": "$type"},
                    "duration_ms": {"$max": "$duration_ms"},
                    "received_at": {"$max": "$received_at"},
                }
            },
            {"$sort": {"received_at": -1, "_id": 1}},
            {"$limit": 200},
        ]
        rows = self.execute(
            lambda: list(self.db().recommendation_interactions.aggregate(pipeline))
        )
        return [
            {
                "listing_id": row["_id"],
                "type": kind,
                "duration_ms": row.get("duration_ms"),
            }
            for row in rows
            for kind in row["types"]
        ]

    def compare_and_update(self, user_id, expected_profile, changes):
        db = self.db()
        from pymongo import ReturnDocument

        return self.execute(
            lambda: db.recommendation_profiles.find_one_and_update(
                {
                    "user_id": user_id,
                    "profile_version": expected_profile["profile_version"],
                    "profile_generation": expected_profile.get("profile_generation"),
                },
                {
                    "$set": {**changes, "updated_at": datetime.now(timezone.utc)},
                    "$inc": {"profile_version": 1},
                },
                return_document=ReturnDocument.AFTER,
            )
        )

    def excluded(self, user_id) -> list[int]:
        return self.execute(
            lambda: self.db().recommendation_interactions.distinct(
                "listing_id", {"user_id": user_id, "type": "not_interested"}
            )
        )

    def close(self):
        if self.client is not None:
            self.client.close()
