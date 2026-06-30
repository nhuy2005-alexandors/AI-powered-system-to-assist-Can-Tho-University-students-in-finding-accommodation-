"""Metric helpers dùng chung cho eval THS2026-66.

Recommendation: precision_at_k, ndcg_at_k, intra_list_similarity
Retrieval/Risk: recall, precision, false_rate
Matching: mean_absolute_error
"""
from __future__ import annotations
import math
from typing import Sequence, Callable


def precision_at_k(recommended: Sequence, relevant: set, k: int = 10) -> float:
    """Tỉ lệ item liên quan trong top-k gợi ý."""
    if k <= 0:
        return 0.0
    topk = list(recommended)[:k]
    hits = sum(1 for item in topk if item in relevant)
    return hits / k


def dcg_at_k(gains: Sequence[float], k: int) -> float:
    return sum(g / math.log2(i + 2) for i, g in enumerate(list(gains)[:k]))


def ndcg_at_k(recommended: Sequence, relevance: dict, k: int = 10) -> float:
    """NDCG@k. relevance: {item: gain}. Item không có trong dict gain=0."""
    gains = [relevance.get(item, 0.0) for item in recommended]
    ideal = sorted(relevance.values(), reverse=True)
    idcg = dcg_at_k(ideal, k)
    if idcg == 0:
        return 0.0
    return dcg_at_k(gains, k) / idcg


def intra_list_similarity(items: Sequence, sim_fn: Callable[[object, object], float]) -> float:
    """ILS = trung bình similarity từng cặp trong danh sách. Thấp = đa dạng."""
    items = list(items)
    n = len(items)
    if n < 2:
        return 0.0
    total = 0.0
    cnt = 0
    for i in range(n):
        for j in range(i + 1, n):
            total += sim_fn(items[i], items[j])
            cnt += 1
    return total / cnt if cnt else 0.0


def recall(tp: int, fn: int) -> float:
    denom = tp + fn
    return tp / denom if denom else 0.0


def precision(tp: int, fp: int) -> float:
    denom = tp + fp
    return tp / denom if denom else 0.0


def false_merge_rate(false_merges: int, total_merges: int) -> float:
    return false_merges / total_merges if total_merges else 0.0


def mean_absolute_error(pred: Sequence[float], true: Sequence[float]) -> float:
    pairs = list(zip(pred, true))
    if not pairs:
        return 0.0
    return sum(abs(p - t) for p, t in pairs) / len(pairs)


if __name__ == "__main__":
    # smoke test
    rec = ["a", "b", "c", "d", "e"]
    rel = {"a", "c", "e"}
    assert abs(precision_at_k(rec, rel, 5) - 0.6) < 1e-9
    relevance = {"a": 3, "b": 0, "c": 2, "d": 0, "e": 1}
    print("P@5 =", precision_at_k(rec, rel, 5))
    print("NDCG@5 =", round(ndcg_at_k(rec, relevance, 5), 4))
    print("MAE =", mean_absolute_error([1, 2, 3], [1, 2, 5]))
    print("OK")
