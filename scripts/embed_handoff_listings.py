"""Generate local E5 embeddings for the internal handoff catalog.

Uses localhost:5454 and prompts for a password. Does not change cleaning status,
source snapshots, or other listing fields. Run --apply-migration first, then
--limit 5 (default) before --all. Existing matching embeddings are reused.
"""
from __future__ import annotations

import argparse
import getpass
import hashlib
import json
from pathlib import Path

import psycopg
from psycopg.rows import dict_row

MODEL = "intfloat/multilingual-e5-small"
ROOT = Path(__file__).resolve().parents[1]


def listing_text(row: dict) -> str:
    fields = (
        ("Tiêu đề", row.get("title")),
        ("Loại nhà", row.get("housing_type")),
        ("Loại chào thuê", row.get("offer_kind")),
        ("Giá nguồn (VND, kỳ giá chưa xác minh)", row.get("price")),
        ("Diện tích (m²)", row.get("area")),
        ("Địa chỉ", row.get("address")),
        ("Quận/huyện", row.get("district")),
        ("Mô tả", row.get("description")),
        ("Trạng thái mô tả", row.get("description_state")),
    )
    lines = [f"{label}: {value}" for label, value in fields if value is not None and value != ""]
    amenities = row.get("parsed_amenities") or {}
    if amenities:
        lines.append("Tiện ích được nêu: " + json.dumps(amenities, ensure_ascii=False, sort_keys=True))
    return "passage: " + "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply-migration", action="store_true")
    scope = parser.add_mutually_exclusive_group()
    scope.add_argument("--limit", type=int)
    scope.add_argument("--all", action="store_true")
    args = parser.parse_args()
    if args.limit is not None and args.limit < 1:
        parser.error("--limit must be positive")

    password = getpass.getpass("Mat khau PostgreSQL handoff: ")
    with psycopg.connect(
        host="localhost", port=5454, dbname="nckh_handoff",
        user="nckh_handoff", password=password, row_factory=dict_row,
    ) as conn:
        if args.apply_migration:
            sql = (ROOT / "infra/db/migrations/93_recommendation_embeddings.sql").read_text(encoding="utf-8")
            conn.execute(sql)
            print("Migration applied: embedding metadata columns are ready.")
            return

        limit = args.limit or 5
        sql = "SELECT * FROM public.catalog_handoff_v1 WHERE status = 'active' ORDER BY id"
        rows = conn.execute(sql if args.all else sql + " LIMIT %s", () if args.all else (limit,)).fetchall()
        # The handoff view was defined using l.* before the metadata migration.
        # Read new metadata from the base table explicitly.
        metadata = {
            row["id"]: row
            for row in conn.execute(
                "SELECT id, embedding_model, embedded_content_hash "
                "FROM public.aggregated_listings"
            ).fetchall()
        }
        conn.commit()
        pending = []
        for row in rows:
            text = listing_text(row)
            digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
            saved = metadata[row["id"]]
            if (row["embedding_vector"] is not None and saved["embedding_model"] == MODEL
                    and saved["embedded_content_hash"] == digest):
                continue
            pending.append((row["id"], text, digest))

        if not pending:
            print(f"Selected {len(rows)} listings; embeddings already up to date.")
            return

        from sentence_transformers import SentenceTransformer

        model = SentenceTransformer(MODEL, device="cpu")
        ready = []
        for listing_id, text, digest in pending:
            token_count = len(model.tokenizer(text, truncation=False)["input_ids"])
            if token_count > model.max_seq_length:
                print(f"Skipped listing {listing_id}: {token_count} tokens exceeds {model.max_seq_length}; review long-text handling.")
                continue
            ready.append((listing_id, text, digest))

        for start in range(0, len(ready), 8):
            batch = ready[start:start + 8]
            vectors = model.encode([item[1] for item in batch], normalize_embeddings=True)
            with conn.transaction():
                for (listing_id, _, digest), vector in zip(batch, vectors):
                    if len(vector) != 384:
                        raise RuntimeError("Expected a 384-dimensional embedding")
                    literal = "[" + ",".join(str(float(value)) for value in vector) + "]"
                    conn.execute(
                        "UPDATE public.aggregated_listings SET embedding_vector = %s::vector, "
                        "embedding_model = %s, embedded_content_hash = %s, embedded_at = now() "
                        "WHERE id = %s", (literal, MODEL, digest, listing_id),
                    )
            print(f"Saved {min(start + 8, len(ready))}/{len(ready)} embeddings.")
        print(f"Selected={len(rows)}, updated={len(ready)}, reused={len(rows) - len(pending)}, long_text_skipped={len(pending) - len(ready)}")


if __name__ == "__main__":
    main()
