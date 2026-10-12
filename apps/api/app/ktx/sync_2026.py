"""One-time publication of the user's 27-room 2026 catalogue."""
from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import create_engine, text

from app.config import settings
from app.ktx.catalog import KtxCatalog
from app.ktx.publishing import prepare_index, publish_index
from app.room_service.chatbot.providers import E5EmbeddingProvider


def main() -> None:
    canonical = json.loads(Path(__file__).with_name("catalog.json").read_text(encoding="utf-8"))
    canonical_rooms = canonical["room_types"]
    if len(canonical_rooms) != 27 or {r["source_id"] for r in canonical_rooms} != {"submitted"}:
        raise RuntimeError("The 2026 seed must contain exactly the 27 submitted room types")
    if any(r["price_period"] != "semester_3_5_months" for r in canonical_rooms):
        raise RuntimeError("Every 2026 room type must use the 3.5-month semester price period")

    engine = create_engine(settings.database_url, pool_pre_ping=True)
    try:
        with engine.connect() as conn:
            year = conn.execute(text("SELECT * FROM ctu_ktx_years WHERE academic_year='2026-2027' AND is_active")).mappings().one()
            current = conn.execute(text("SELECT payload,content_sha256 FROM ctu_ktx_catalog WHERE id=1")).mappings().one()
            original_hash = current["content_sha256"]
        if len(current["payload"]["room_types"]) == 27 and current["payload"].get("version", "").startswith("ktx-2026-user-catalog"):
            print("2026 catalogue already published")
            return
        if year["revision"] != 1 or year["archived"] or not year["is_active"] or year["payload"] != year["published_payload"]:
            raise RuntimeError("The active year has changed; refusing to overwrite administrator edits")
        old_rooms = current["payload"]["room_types"]
        if Counter(r["source_id"] for r in old_rooms) != Counter({"submitted": 27, "ctu_2025": 16}):
            raise RuntimeError("The previous 27+16 room catalogue was not found")
        old_by_code = {r["code"]: r for r in old_rooms if r["source_id"] == "submitted"}
        if len(old_by_code) != 27 or any(old_by_code[r["code"]]["price"] != r["price"] for r in canonical_rooms):
            raise RuntimeError("The 27 prices no longer match the user's supplied catalogue")

        next_data = dict(current["payload"])
        for key in ("room_types", "sources", "facts", "dormitories"):
            next_data[key] = canonical[key]
        next_data["term"] = canonical.get("term", "")
        next_data["academic_year"] = "2026-2027"
        next_data["version"] = "ktx-2026-user-catalog-" + datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        next_data["updated_at"] = datetime.now(timezone.utc).date().isoformat()
        catalog = KtxCatalog.model_validate(next_data)
        model = settings.chatbot_embedding_model
        records, count_new = prepare_index(engine, catalog, E5EmbeddingProvider(model), model)

        with engine.begin() as conn:
            conn.execute(text("SELECT pg_advisory_xact_lock(hashtext('ctu-ktx-catalog'))"))
            locked = conn.execute(text("SELECT * FROM ctu_ktx_years WHERE id=:id FOR UPDATE"), {"id": year["id"]}).mappings().one()
            stored_hash = conn.execute(text("SELECT content_sha256 FROM ctu_ktx_catalog WHERE id=1 FOR UPDATE")).scalar_one()
            if locked["revision"] != year["revision"] or stored_hash != original_hash or not locked["is_active"]:
                raise RuntimeError("The catalogue changed during indexing; nothing was published")
            checksum = publish_index(conn, catalog, records, model)
            body = catalog.model_dump_json()
            conn.execute(text("UPDATE ctu_ktx_years SET payload=CAST(:body AS jsonb),published_payload=CAST(:body AS jsonb),"
                "revision=revision+1,published_at=now(),updated_at=now() WHERE id=:id"),
                {"body": body, "id": year["id"]})
            after = conn.execute(text("SELECT * FROM ctu_ktx_years WHERE id=:id"), {"id": year["id"]}).mappings().one()
            conn.execute(text("INSERT INTO ctu_ktx_admin_audit(year_id,action,before_data,after_data) "
                "VALUES(:id,'import_2026_user_catalog',CAST(:before AS jsonb),CAST(:after AS jsonb))"),
                {"id": year["id"], "before": json.dumps(dict(year), default=str, ensure_ascii=False),
                 "after": json.dumps(dict(after), default=str, ensure_ascii=False)})
        print(json.dumps({"year": catalog.academic_year, "room_types": len(catalog.room_types),
            "new_vectors": count_new, "indexed_records": len(records), "checksum": checksum}, ensure_ascii=False))
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
