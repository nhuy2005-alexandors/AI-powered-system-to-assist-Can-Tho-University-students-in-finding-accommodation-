"""Create real 384-D E5 embeddings for stale development listings.

No fallback vector is written. If the model is unavailable the command exits
clearly, leaving embedding_vector NULL so the API reports degraded mode.
"""
from __future__ import annotations

import argparse
import hashlib
import json

from db_connection import local_database_url


def canonical_text(row: dict) -> str:
    amenities = row.get("parsed_amenities") or {}
    return " | ".join(
        str(value or "")
        for value in (
            row.get("title"),
            row.get("description"),
            row.get("address"),
            row.get("district"),
            row.get("price"),
            row.get("area"),
            json.dumps(amenities, sort_keys=True, ensure_ascii=False),
        )
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--database-url")
    parser.add_argument("--model", default="intfloat/multilingual-e5-small")
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--limit", type=int)
    args = parser.parse_args()
    try:
        import psycopg
        from sentence_transformers import SentenceTransformer
    except ImportError as exc:
        raise SystemExit(
            "Degraded mode: cần cài apps/api/requirements-ml.txt để tạo embedding E5 thật"
        ) from exc

    model = SentenceTransformer(args.model)
    limit_sql = " LIMIT %s" if args.limit else ""
    params = (args.limit,) if args.limit else ()
    with psycopg.connect(local_database_url(args.database_url), autocommit=True) as conn:
        rows = conn.execute(
            "SELECT id, title, description, address, district, price, area, parsed_amenities "
            "FROM aggregated_listings WHERE status = 'active' AND cleaning_status = 'cleaned' "
            "ORDER BY id" + limit_sql,
            params,
        ).fetchall()
        records = []
        for row in rows:
            data = dict(zip(("id", "title", "description", "address", "district", "price", "area", "parsed_amenities"), row))
            content = canonical_text(data)
            records.append((data["id"], content, hashlib.sha256(content.encode("utf-8")).hexdigest()))

        for start in range(0, len(records), args.batch_size):
            batch = records[start : start + args.batch_size]
            vectors = model.encode(
                [f"passage: {item[1]}" for item in batch], normalize_embeddings=True
            )
            for (listing_id, _, digest), vector in zip(batch, vectors):
                if len(vector) != 384:
                    raise RuntimeError("Embedding model không trả đúng 384 chiều")
                literal = "[" + ",".join(f"{float(value):.9g}" for value in vector) + "]"
                conn.execute(
                    "UPDATE aggregated_listings SET embedding_vector = %s::vector, "
                    "embedding_model = %s, embedded_content_hash = %s, embedded_at = now() "
                    "WHERE id = %s",
                    (literal, args.model, digest, listing_id),
                )
    print(f"Embedded {len(records)} listings with {args.model}")


if __name__ == "__main__":
    main()
