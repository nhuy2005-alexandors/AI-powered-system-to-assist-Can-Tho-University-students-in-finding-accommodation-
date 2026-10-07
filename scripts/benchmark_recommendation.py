"""Compare CPU rerank settings on real listings without changing stored data."""
from __future__ import annotations

import argparse
import getpass
import json
import math
import os
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps/api"))

CASES = [
    {"needs": "Phòng có máy lạnh, nhà vệ sinh riêng, gần Đại học Cần Thơ", "max_price": 3_000_000},
    {"needs": "Phòng trọ có gác, chỗ nấu ăn riêng, phù hợp sinh viên", "max_price": 2_000_000},
    {"needs": "Phòng có nội thất, máy lạnh, chỗ để xe", "max_price": 3_000_000, "district": "Quận Ninh Kiều"},
]
# candidate count, pair token limit, batch size, CPU intra-op threads
VARIANTS = {
    "baseline": (50, 512, 2, 8),
    "initial_tuning": (20, 384, 4, 8),
    "four_threads": (20, 384, 4, 4),
    "full_length": (20, 512, 2, 4),
    "sorted_batch2": (50, 512, 2, 8),
    "sorted_batch4": (50, 512, 4, 8),
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--variants", nargs="+", choices=VARIANTS, default=["baseline", "sorted_batch2"])
    parser.add_argument("--cases", nargs="+", type=int, choices=range(1, len(CASES) + 1), default=[1, 2, 3])
    parser.add_argument("--repeats", type=int, default=1)
    parser.add_argument("--offline", action="store_true", help="Require models already in the local Hugging Face cache")
    args = parser.parse_args()
    if args.repeats < 1:
        parser.error("repeats must be positive")
    if args.offline:
        os.environ["HF_HUB_OFFLINE"] = "1"
    import torch
    from sentence_transformers import CrossEncoder
    from sqlalchemy import URL, create_engine, text
    from app.room_service.recommendation.models import EMBEDDING_MODEL, RERANKER_MODEL, LocalModels, room_text
    from app.room_service.recommendation.repo import ListingRepository
    from app.room_service.recommendation.schemas import Preferences

    url = os.environ.get("RECOMMENDATION_BENCHMARK_DATABASE_URL")
    if not url:
        url = URL.create("postgresql+psycopg", username="nckh_handoff", password=getpass.getpass("PostgreSQL handoff password: "), host="127.0.0.1", port=5454, database="nckh_handoff")
    engine = create_engine(url, pool_pre_ping=True)
    repo = ListingRepository(engine)
    with engine.connect() as conn:
        counts = conn.execute(text("SELECT count(*) AS listings, count(embedding_vector) AS embedded FROM aggregated_listings")).mappings().one()
    report = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "platform": platform.platform(), "torch": torch.__version__,
        "embedding_model": EMBEDDING_MODEL, "reranker_model": RERANKER_MODEL,
        "dataset": dict(counts), "offline": args.offline, "runs": [],
        "scope": "Sequential local CPU microbenchmark. No human relevance labels; top-10 overlap is stability, not accuracy. Model load measured separately. No response cache.",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)

    def save():
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    torch.set_num_threads(8)
    local = LocalModels()
    inputs = []
    for case_id in args.cases:
        prefs = Preferences(**CASES[case_id - 1])
        started = perf_counter()
        vector = local.embed(prefs)
        embed_ms = round((perf_counter() - started) * 1000)
        started = perf_counter()
        rows = repo.search(vector, prefs, EMBEDDING_MODEL, 50, [])
        retrieval_ms = round((perf_counter() - started) * 1000)
        query = prefs.needs + (f" Khu vực: {prefs.district}." if prefs.district else "")
        inputs.append((case_id, prefs, rows, query, embed_ms, retrieval_ms))
    # Release E5 before measuring BGE; the API keeps both, so also measure HTTP separately.
    del local
    import gc
    gc.collect()
    started = perf_counter()
    model = CrossEncoder(RERANKER_MODEL, device="cpu", max_length=512)
    report["reranker_load_ms"] = round((perf_counter() - started) * 1000)
    save()
    print(json.dumps({"stage": "model_loaded", "load_ms": report["reranker_load_ms"]}), flush=True)
    for case_id, prefs, rows, query, embed_ms, retrieval_ms in inputs:
        for name in args.variants:
            candidates, max_length, batch_size, threads = VARIANTS[name]
            torch.set_num_threads(threads)
            model.max_length = max_length
            selected = rows[:candidates]
            pairs = [(query, room_text(row)) for row in selected]
            for repeat in range(args.repeats):
                print(json.dumps({"stage": "start", "case": case_id, "variant": name, "repeat": repeat + 1}), flush=True)
                started = perf_counter()
                lengths = [len(model.tokenizer(a, b, truncation=False)["input_ids"]) for a, b in pairs]
                truncated = sum(length > max_length for length in lengths)
                order = sorted(range(len(pairs)), key=lambda i: min(lengths[i], max_length)) if name.startswith("sorted_") else list(range(len(pairs)))
                predictions = model.predict([pairs[i] for i in order], batch_size=batch_size, activation_fct=torch.nn.Identity(), show_progress_bar=False) if pairs else []
                if len(predictions) != len(pairs) or not all(math.isfinite(float(score)) for score in predictions):
                    raise RuntimeError("Invalid model scores")
                scores = [0.0] * len(pairs)
                for index, score in zip(order, predictions):
                    scores[index] = score
                elapsed = round((perf_counter() - started) * 1000)
                scored = [{"listing_id": row["id"], "title": row["title"], "price": row["price"], "cosine_rank": rank, "score": float(score)} for rank, (row, score) in enumerate(zip(selected, scores), 1)]
                scored.sort(key=lambda row: (-row["score"], row["cosine_rank"]))
                run = {"case": case_id, "preferences": prefs.model_dump(), "variant": name, "repeat": repeat + 1, "candidates": len(selected), "max_length": max_length, "batch_size": batch_size, "threads": threads, "truncated_pairs": truncated, "embed_ms": embed_ms, "retrieval_ms": retrieval_ms, "rerank_ms": elapsed, "eligible_count": rows[0]["eligible_count"] if rows else 0, "top10": scored[:10]}
                report["runs"].append(run)
                save()
                print(json.dumps({"stage": "done", "case": case_id, "variant": name, "repeat": repeat + 1, "rerank_ms": elapsed, "truncated": truncated, "top10": [row["listing_id"] for row in scored[:10]]}), flush=True)
    engine.dispose()


if __name__ == "__main__":
    main()
