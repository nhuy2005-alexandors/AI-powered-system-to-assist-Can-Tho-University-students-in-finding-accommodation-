"""Evaluate ranked recommendations using independent survey/manual relevance labels."""
from __future__ import annotations

import argparse
import json
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "eval"))

from metrics import ndcg_at_k, precision_at_k  # noqa: E402

ALLOWED_LABEL_SOURCES = {"manual", "student_survey", "held_out_interaction"}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=ROOT / "eval/reports/recommendation_eval.json")
    parser.add_argument("--k", type=int, default=10)
    args = parser.parse_args()
    if args.k <= 0:
        raise SystemExit("k phải lớn hơn 0")

    rows = [json.loads(line) for line in args.dataset.read_text(encoding="utf-8").splitlines() if line.strip()]
    if not rows:
        raise SystemExit("Dataset rỗng; cần relevance judgment độc lập trước khi đánh giá gợi ý.")
    invalid = [row.get("user_id") for row in rows if row.get("label_source") not in ALLOWED_LABEL_SOURCES]
    if invalid:
        raise SystemExit(f"Nhãn không độc lập ở users: {invalid[:10]}")

    precisions: list[float] = []
    ndcgs: list[float] = []
    for row in rows:
        recommended = row["recommended_ids"]
        relevance = {str(key): float(value) for key, value in row["relevance"].items()}
        recommended = [str(value) for value in recommended]
        precisions.append(precision_at_k(recommended, {key for key, gain in relevance.items() if gain > 0}, args.k))
        ndcgs.append(ndcg_at_k(recommended, relevance, args.k))
    report = {
        "evaluation_scope": "independent_relevance_labels",
        "users": len(rows),
        "k": args.k,
        "metrics": {
            f"precision_at_{args.k}": round(statistics.mean(precisions), 4),
            f"ndcg_at_{args.k}": round(statistics.mean(ndcgs), 4),
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
