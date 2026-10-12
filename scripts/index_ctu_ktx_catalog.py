"""Atomically import the shared KTX catalogue and real 384-dimensional E5 vectors."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps/api"))
from sqlalchemy import create_engine, text
from app.config import settings
from app.ktx.catalog import KtxCatalog, fold_text, room_text
from app.room_service.chatbot.providers import E5EmbeddingProvider


def records(catalog):
    for room in catalog.room_types:
        yield dict(id=room.id, kind="room_type", source_id=room.source_id, content=room_text(room,catalog.academic_year), metadata=room.model_dump())
    for area in catalog.dormitories:
        location = area.location
        content = (f"KTX Đại học Cần Thơ {area.name}. {area.description} {area.buildings}. "
                   f"Khoảng {area.capacity} sinh viên. Tọa độ GPS: {location.lat}, {location.lng}. "
                   f"{location.label}; điểm đại diện theo OpenStreetMap, không phải tọa độ từng phòng hay cổng vào. "
                   f"Liên hệ {area.phone}.")
        yield dict(id="dormitory-" + area.id, kind="dormitory", source_id="intro", content=content, metadata=area.model_dump())
    for fact in catalog.facts:
        yield dict(id="fact-" + fact.id, kind="fact", source_id=fact.source_id,
                   content=fact.title + ": " + fact.content, metadata=fact.model_dump())
    manifest_path = ROOT / "docs/ctu_ktx_corpus_20261007/manifest.json"
    mapping = {"ctu-2026-registration": "registration", "ctu-new-students": "new_students",
               "ctu-ktx-rules": "rules", "ctu-ktx-facilities": "facilities"}
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for entry in manifest["documents"]:
        path = ROOT / entry["file"]
        if hashlib.sha256(path.read_bytes()).hexdigest() != entry["sha256"]:
            raise ValueError("Source checksum mismatch: " + entry["id"])
        data = json.loads(path.read_text(encoding="utf-8"))
        for index, clause in enumerate(data["provisions"]):
            content = clause["heading"] + "\n" + clause["content"]
            yield dict(id=f"clause-{entry['id']}-{index}", kind="source_clause",
                       source_id=mapping[entry["id"]], content=content,
                       metadata=dict(heading=clause["heading"], source_url=data["source"].get("source_url"),
                                     page_from=clause.get("page_from"), page_to=clause.get("page_to")))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--catalog", type=Path, default=ROOT / "apps/api/app/ktx/catalog.json")
    parser.add_argument("--report", type=Path, default=ROOT / "docs/ktx_catalog_index_report.json")
    parser.add_argument("--allow-model-download", action="store_true", help="Download E5 if the local cache is empty")
    args = parser.parse_args()
    raw = args.catalog.read_bytes()
    catalog = KtxCatalog.model_validate_json(raw)
    entries = list(records(catalog))
    engine = create_engine(settings.database_url, pool_pre_ping=True)
    with engine.begin() as conn:
        conn.exec_driver_sql((ROOT / "infra/db/migrations/103_ctu_dormitories.sql").read_text(encoding="utf-8"))
        old = {row["id"]: dict(row) for row in conn.execute(text(
            "SELECT id,content_sha256,embedding_model,embedding_vector::text AS vector FROM ctu_ktx_search_documents"
        )).mappings()}
    embedder = E5EmbeddingProvider(settings.chatbot_embedding_model, allow_download=args.allow_model_download)
    pending = []
    for record in entries:
        record["content_sha256"] = hashlib.sha256(record["content"].encode()).hexdigest()
        prior = old.get(record["id"])
        if prior and prior["content_sha256"] == record["content_sha256"] and prior["embedding_model"] == settings.chatbot_embedding_model:
            record["vector"] = json.loads(prior["vector"])
        else:
            pending.append(record)
    for offset in range(0, len(pending), 16):
        batch = pending[offset:offset + 16]
        vectors = embedder.embed_passages([entry["content"] for entry in batch])
        if len(vectors) != len(batch):
            raise ValueError("Embedding batch is incomplete")
        for entry, vector in zip(batch, vectors):
            if len(vector) != 384 or not all(math.isfinite(v) for v in vector) or not any(vector):
                raise ValueError("Invalid E5 vector")
            entry["vector"] = vector
        print(f"Embedded {min(offset + 16, len(pending))}/{len(pending)}", flush=True)
    with engine.begin() as conn:
        conn.execute(text("SELECT pg_advisory_xact_lock(hashtext('ctu-ktx-catalog'))"))
        for record in entries:
            conn.execute(text(
                "INSERT INTO ctu_ktx_search_documents(id,kind,source_id,content,normalized_content,metadata,content_sha256,embedding_vector,embedding_model) "
                "VALUES(:id,:kind,:source_id,:content,:normalized,CAST(:metadata AS jsonb),:hash,CAST(:vector AS vector),:model) "
                "ON CONFLICT(id) DO UPDATE SET kind=EXCLUDED.kind,source_id=EXCLUDED.source_id,content=EXCLUDED.content,"
                "normalized_content=EXCLUDED.normalized_content,metadata=EXCLUDED.metadata,content_sha256=EXCLUDED.content_sha256,"
                "embedding_vector=EXCLUDED.embedding_vector,embedding_model=EXCLUDED.embedding_model,embedded_at=now()"
            ), dict(id=record["id"], kind=record["kind"], source_id=record["source_id"], content=record["content"],
                    normalized=fold_text(record["content"]), metadata=json.dumps(record["metadata"], ensure_ascii=False),
                    hash=record["content_sha256"], vector=json.dumps(record["vector"]), model=settings.chatbot_embedding_model))
        conn.execute(text("DELETE FROM ctu_ktx_search_documents WHERE NOT(id = ANY(:ids))"), {"ids": [r["id"] for r in entries]})
        checksum = hashlib.sha256(raw).hexdigest()
        conn.execute(text(
            "INSERT INTO ctu_ktx_catalog(id,payload,content_sha256) VALUES(1,CAST(:payload AS jsonb),:hash) "
            "ON CONFLICT(id) DO UPDATE SET payload=EXCLUDED.payload,content_sha256=EXCLUDED.content_sha256,updated_at=now()"
        ), dict(payload=json.dumps(catalog.model_dump(), ensure_ascii=False), hash=checksum))
        counts = dict(conn.execute(text(
            "SELECT count(*) AS records,count(embedding_vector) AS vectors FROM ctu_ktx_search_documents"
        )).mappings().one())
    report = dict(version=catalog.version, rooms=len(catalog.room_types), images=len(catalog.images),
                  dormitories=len(catalog.dormitories), facts=len(catalog.facts), newly_embedded=len(pending),
                  embedding_model=settings.chatbot_embedding_model, dimensions=384, sha256=checksum, **counts)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False), flush=True)
    engine.dispose()


if __name__ == "__main__":
    main()
