from __future__ import annotations

import math
from collections import Counter
from typing import Any

from sqlalchemy import text
from sqlalchemy.engine import Engine

from .providers import normalize_text
from .schemas import ChatFilters


STOP_WORDS = {
    "anh", "ban", "can", "cho", "co", "cua", "duoc", "giup", "la",
    "minh", "nha", "phong", "tim", "toi", "tro", "va", "voi",
}


def _vector_literal(vector: list[float]) -> str:
    return "[" + ",".join(f"{value:.9g}" for value in vector) + "]"


def _tokens(value: str) -> list[str]:
    return [
        token
        for token in normalize_text(value).split()
        if len(token) > 1 and token not in STOP_WORDS
    ]


def _listing_document(item: dict[str, Any]) -> str:
    amenities = item.get("parsed_amenities") or {}
    enabled_amenities = " ".join(
        key.replace("_", " ") for key, enabled in amenities.items() if enabled is True
    )
    # Repeating title and district gives important short fields more BM25 weight.
    return " ".join(
        str(value or "")
        for value in (
            item.get("title"), item.get("title"), item.get("description"),
            item.get("address"), item.get("district"), item.get("district"),
            enabled_amenities, item.get("listing_type"),
        )
    )


def bm25_scores(
    query: str,
    documents: list[str],
    *,
    k1: float = 1.5,
    b: float = 0.75,
) -> list[float]:
    """BM25 from the old Hybrid project, adapted to live listing rows."""

    if not documents:
        return []
    query_terms = Counter(_tokens(query))
    tokenized = [_tokens(document) for document in documents]
    if not query_terms or not any(tokenized):
        return [0.0] * len(documents)

    document_frequency: Counter[str] = Counter()
    for tokens in tokenized:
        document_frequency.update(set(tokens))
    average_length = sum(len(tokens) for tokens in tokenized) / len(tokenized) or 1.0
    total = len(tokenized)
    raw_scores: list[float] = []
    for tokens in tokenized:
        frequencies = Counter(tokens)
        length_norm = k1 * (1 - b + b * len(tokens) / average_length)
        score = 0.0
        for term, query_count in query_terms.items():
            frequency = frequencies.get(term, 0)
            if not frequency:
                continue
            inverse_frequency = math.log(
                1 + (total - document_frequency[term] + 0.5) / (document_frequency[term] + 0.5)
            )
            score += query_count * inverse_frequency * (frequency * (k1 + 1)) / (
                frequency + length_norm
            )
        raw_scores.append(score)
    maximum = max(raw_scores, default=0.0)
    return [score / maximum if maximum > 0 else 0.0 for score in raw_scores]


def _preference_score(
    filters: ChatFilters, item: dict[str, Any]
) -> tuple[float, list[str]]:
    checks: list[tuple[bool, str]] = []
    price = item.get("price")
    area = item.get("area")
    distance = item.get("distance_to_ctu")
    route_times = [
        value for value in (item.get("route_time_campus") or []) if value is not None
    ]
    amenities = item.get("parsed_amenities") or {}

    if filters.min_price is not None:
        checks.append((price is not None and price >= filters.min_price, "Đúng mức giá"))
    if filters.max_price is not None:
        checks.append((price is not None and price <= filters.max_price, "Trong ngân sách"))
    if filters.min_area is not None:
        checks.append((area is not None and area >= filters.min_area, "Đủ diện tích"))
    if filters.district:
        checks.append(
            (
                filters.district.lower() in str(item.get("district") or "").lower(),
                f"Khu vực {filters.district}",
            )
        )
    if filters.max_distance_ctu is not None:
        checks.append(
            (distance is not None and distance <= filters.max_distance_ctu, "Gần CTU")
        )
    if filters.max_route_minutes is not None:
        checks.append(
            (
                bool(route_times) and min(route_times) <= filters.max_route_minutes,
                "Đúng thời gian di chuyển",
            )
        )
    for amenity in filters.amenities:
        checks.append((amenities.get(amenity) is True, "Đủ tiện ích yêu cầu"))

    if not checks:
        return 0.55, []
    matched = [reason for passed, reason in checks if passed]
    return sum(passed for passed, _ in checks) / len(checks), list(dict.fromkeys(matched))


class ChatRepository:
    """Read-only repository for stateless hybrid housing retrieval."""

    def __init__(self, engine: Engine):
        self.engine = engine

    def retrieve(
        self,
        query: str,
        filters: ChatFilters,
        vector: list[float] | None,
        limit: int = 5,
    ) -> list[dict]:
        clauses = ["status = 'active'", "cleaning_status = 'cleaned'"]
        params: dict[str, Any] = {"candidate_limit": 250}
        if filters.listing_type:
            clauses.append("listing_type = CAST(:listing_type AS listing_type_enum)")
            params["listing_type"] = filters.listing_type
        if filters.min_price is not None:
            clauses.append("price >= :min_price")
            params["min_price"] = filters.min_price
        if filters.max_price is not None:
            clauses.append("price <= :max_price")
            params["max_price"] = filters.max_price
        if filters.min_area is not None:
            clauses.append("area >= :min_area")
            params["min_area"] = filters.min_area
        if filters.district:
            clauses.append("district ILIKE :district")
            params["district"] = f"%{filters.district}%"
        if filters.max_distance_ctu is not None:
            clauses.append("distance_to_ctu <= :max_distance")
            params["max_distance"] = filters.max_distance_ctu
        if filters.max_route_minutes is not None:
            clauses.append(
                "LEAST(COALESCE(route_time_campus[1], 1e9), "
                "COALESCE(route_time_campus[2], 1e9), COALESCE(route_time_campus[3], 1e9)) "
                "<= :max_minutes"
            )
            params["max_minutes"] = filters.max_route_minutes
        for index, amenity in enumerate(filters.amenities):
            key = f"amenity_{index}"
            clauses.append(
                f"COALESCE((parsed_amenities ->> :{key})::boolean, false) IS TRUE"
            )
            params[key] = amenity
        if filters.gender:
            clauses.append(
                "COALESCE(parsed_amenities ->> 'gender', 'any') IN ('any', :gender)"
            )
            params["gender"] = filters.gender

        if vector is not None:
            vector_sql = (
                "CASE WHEN embedding_vector IS NULL THEN 0 ELSE "
                "GREATEST(0, LEAST(1, 1 - (embedding_vector <=> CAST(:query_vector AS vector)))) END"
            )
            params["query_vector"] = _vector_literal(vector)
            order_sql = "vector_score DESC, quality_score DESC NULLS LAST"
        else:
            vector_sql = "0"
            order_sql = "quality_score DESC NULLS LAST, freshness_score DESC NULLS LAST"

        sql = text(
            "SELECT id, title, price, area, address, district, description, parsed_amenities, "
            "distance_to_ctu, route_time_campus, source, source_url, quality_score, "
            "freshness_score, risk_score, listing_type, "
            f"{vector_sql} AS vector_score FROM aggregated_listings "
            f"WHERE {' AND '.join(clauses)} ORDER BY {order_sql} LIMIT :candidate_limit"
        )
        with self.engine.connect() as conn:
            rows = [dict(row) for row in conn.execute(sql, params).mappings().all()]

        lexical_scores = bm25_scores(query, [_listing_document(item) for item in rows])
        for item, bm25_score in zip(rows, lexical_scores):
            vector_score = float(item.get("vector_score") or 0.0)
            quality = max(0.0, min(1.0, float(item.get("quality_score") or 0.0)))
            freshness = max(0.0, min(1.0, float(item.get("freshness_score") or 0.0)))
            safety = 1.0 - max(0.0, min(1.0, float(item.get("risk_score") or 0.0)))
            distance = item.get("distance_to_ctu")
            proximity = (
                1.0 / (1.0 + max(0.0, float(distance)) / 2000)
                if distance is not None
                else 0.25
            )
            preference, reasons = _preference_score(filters, item)

            if vector is None:
                final_score = (
                    0.45 * bm25_score
                    + 0.22 * preference
                    + 0.14 * quality
                    + 0.10 * freshness
                    + 0.06 * safety
                    + 0.03 * proximity
                )
            else:
                final_score = (
                    0.35 * vector_score
                    + 0.25 * bm25_score
                    + 0.15 * preference
                    + 0.10 * quality
                    + 0.08 * freshness
                    + 0.05 * safety
                    + 0.02 * proximity
                )
            if vector_score >= 0.6:
                reasons.insert(0, "Khớp ngữ nghĩa")
            if bm25_score >= 0.5:
                reasons.insert(0, "Khớp từ khóa")
            if quality >= 0.75:
                reasons.append("Tin chất lượng tốt")
            item["bm25_score"] = round(bm25_score, 6)
            item["similarity_score"] = round(max(0.0, min(1.0, final_score)), 6)
            item["match_reasons"] = list(dict.fromkeys(reasons))[:3]

        rows.sort(
            key=lambda item: (
                -item["similarity_score"],
                -float(item.get("quality_score") or 0.0),
                item["id"],
            )
        )
        for rank, item in enumerate(rows[:limit], 1):
            item["rank"] = rank
        return rows[:limit]
