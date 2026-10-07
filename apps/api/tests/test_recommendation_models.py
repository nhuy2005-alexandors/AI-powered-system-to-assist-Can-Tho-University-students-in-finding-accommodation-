"""Rerank batching and score-cache invariants without loading ML weights."""
from copy import deepcopy
from types import SimpleNamespace
import sys

import pytest
from fastapi import HTTPException

from app.room_service.recommendation import models
from app.room_service.recommendation.schemas import Preferences


@pytest.fixture
def runner(monkeypatch):
    class Encoder:
        def __init__(self):
            self.calls = []
            self.bad_scores = False

        def tokenizer(self, query, document, **kwargs):
            return {"input_ids": list(range(len(query) + len(document)))}

        def predict(self, pairs, **kwargs):
            self.calls.append(pairs)
            return [float("nan") if self.bad_scores else float(len(doc)) for _, doc in pairs]

    monkeypatch.setitem(sys.modules, "torch", SimpleNamespace(nn=SimpleNamespace(Identity=lambda: None)))
    monkeypatch.setitem(sys.modules, "sentence_transformers", SimpleNamespace(CrossEncoder=lambda *a, **kw: Encoder()))
    clock = [100.0]
    monkeypatch.setattr(models, "monotonic", lambda: clock[0])
    local = models.LocalModels()
    local.reranker = Encoder()
    return local, clock


def preferences(needs="A quiet room"):
    return Preferences(needs=needs, max_price=3_000_000)


def rows():
    return [
        {"id": 1, "title": "Long description " * 50, "price": 2_000_000, "cosine_rank": 1},
        {"id": 2, "title": "Short room", "price": 1_000_000, "cosine_rank": 2},
    ]


def test_sorted_batches_keep_scores_attached_to_the_correct_room(runner):
    local, _ = runner
    result, truncated = local.rerank(preferences(), rows())
    assert "Short room" in local.reranker.calls[0][0][1]
    assert [row["id"] for row in result] == [1, 2]
    assert result[0]["rerank_score"] > result[1]["rerank_score"]
    assert truncated == 1


def test_repeated_request_uses_scores_and_preserves_truncation_warning(runner):
    local, _ = runner
    first = local.rerank(preferences(), rows())
    second = local.rerank(preferences(), rows())
    assert first == second
    assert len(local.reranker.calls) == 1


def test_changed_room_or_needs_recomputes_only_affected_pairs(runner):
    local, _ = runner
    local.rerank(preferences(), rows())
    changed = rows()
    changed[0]["price"] = 2_500_000
    local.rerank(preferences(), changed)
    assert len(local.reranker.calls[-1]) == 1
    local.rerank(preferences("Room with air conditioning"), changed)
    assert len(local.reranker.calls[-1]) == 2


def test_cache_does_not_restore_removed_candidates_or_old_cosine_rank(runner):
    local, _ = runner
    local.rerank(preferences(), rows())
    remaining = rows()[1:]
    remaining[0]["cosine_rank"] = 1
    result, _ = local.rerank(preferences(), remaining)
    assert [row["id"] for row in result] == [2]
    assert result[0]["cosine_rank"] == 1
    assert len(local.reranker.calls) == 1


def test_expired_scores_are_recomputed(runner):
    local, clock = runner
    local.rerank(preferences(), rows())
    clock[0] += models.RERANK_CACHE_TTL_SECONDS
    local.rerank(preferences(), rows())
    assert len(local.reranker.calls) == 2


def test_cache_is_bounded_and_keeps_recently_used_scores(runner, monkeypatch):
    local, _ = runner
    monkeypatch.setattr(models, "RERANK_CACHE_SIZE", 2)
    local.rerank(preferences(), rows())
    local.rerank(preferences(), rows()[:1])
    third = {"id": 3, "title": "Third", "cosine_rank": 1}
    local.rerank(preferences(), [third])
    assert len(local.rerank_cache) == 2
    count = len(local.reranker.calls)
    local.rerank(preferences(), rows()[:1])
    assert len(local.reranker.calls) == count
    local.rerank(preferences(), rows()[1:])
    assert len(local.reranker.calls) == count + 1


def test_invalid_scores_are_not_cached_or_written_to_rows(runner):
    local, _ = runner
    local.reranker.bad_scores = True
    candidates = rows()
    before = deepcopy(candidates)
    with pytest.raises(HTTPException) as exc:
        local.rerank(preferences(), candidates)
    assert exc.value.status_code == 503
    assert not local.rerank_cache
    assert candidates == before
    local.reranker.bad_scores = False
    assert len(local.rerank(preferences(), candidates)[0]) == 2


def test_empty_candidates_skip_inference(runner):
    local, _ = runner
    assert local.rerank(preferences(), []) == ([], 0)
    assert not local.reranker.calls
