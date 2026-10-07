"""Offline behavior-learning tests: no databases or downloaded models required."""
from copy import deepcopy
from datetime import datetime, timezone
from math import sqrt

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from app.room_service.recommendation import behavior, service as service_module
from app.room_service.recommendation.models import EMBEDDING_MODEL, RERANKER_MODEL
from app.room_service.recommendation.router import (
    get_recommendation_user_id,
    get_service,
    router,
)
from app.room_service.recommendation.schemas import InteractionIn, Preferences


USER_ID = "postgres:42"
NOW = datetime(2026, 10, 7, tzinfo=timezone.utc)


def axis(index):
    vector = [0.0] * behavior.VECTOR_DIMENSIONS
    vector[index] = 1.0
    return vector


def signal(listing_id, kind="contact", duration_ms=None, generation="generation-1"):
    return {
        "listing_id": listing_id,
        "type": kind,
        "duration_ms": duration_ms,
        "received_at": NOW,
        "profile_generation": generation,
    }


def preferences(**overrides):
    return Preferences(**{
        "needs": "A room near campus",
        "max_price": 2_000_000,
        "district": "Ninh Kieu",
        **overrides,
    })


def profile(initial=None, **overrides):
    initial = axis(0) if initial is None else initial
    return {
        "user_id": USER_ID,
        "preferences": preferences().model_dump(),
        "initial_vector": deepcopy(initial),
        "preference_vector": deepcopy(initial),
        "embedding_model": EMBEDDING_MODEL,
        "profile_version": 1,
        "profile_generation": "generation-1",
        "behavior_since": NOW,
        "behavior_listing_count": 0,
        "behavior_weight": 0.0,
        "behavior_blend": 0.0,
        "behavior_signal_weights": {},
        "updated_at": NOW,
        **overrides,
    }


def listing(listing_id, vector, **overrides):
    return {
        "id": listing_id,
        "title": f"Room {listing_id}",
        "price": 1_800_000,
        "district": "Ninh Kieu",
        "embedding_vector": vector,
        "embedding_model": EMBEDDING_MODEL,
        **overrides,
    }


class FakeModels:
    def __init__(self):
        self.vector = axis(0)
        self.embed_calls = []
        self.rerank_calls = []

    def embed(self, value):
        self.embed_calls.append(value.model_dump())
        return deepcopy(self.vector)

    def rerank(self, value, rows):
        self.rerank_calls.append((value.model_dump(), deepcopy(rows)))
        for index, row in enumerate(rows):
            row["rerank_score"] = float(index)
        return list(reversed(rows)), 0


class MemoryListings:
    def __init__(self, rows):
        self.rows = deepcopy(rows)
        self.search_calls = []
        self.embedding_calls = []

    def exists(self, listing_id):
        return any(row["id"] == listing_id for row in self.rows)

    def embeddings(self, listing_ids, model):
        self.embedding_calls.append((list(listing_ids), model))
        return {
            row["id"]: deepcopy(row["embedding_vector"])
            for row in self.rows
            if row["id"] in listing_ids
            and row.get("embedding_model") == model
            and row.get("embedding_vector") is not None
        }

    def search(self, vector, value, model, limit, excluded):
        self.search_calls.append({
            "vector": deepcopy(vector),
            "preferences": value.model_dump(),
            "model": model,
            "limit": limit,
            "excluded": list(excluded),
        })
        rows = [deepcopy(row) for row in self.rows
                if 0 < row["price"] <= value.max_price
                and (not value.district or row["district"] == value.district)
                and row["id"] not in excluded
                and row.get("embedding_model") == model
                and row.get("embedding_vector") is not None]
        for row in rows:
            row["cosine_score"] = sum(a * b for a, b in zip(vector, row["embedding_vector"]))
            row["eligible_count"] = len(rows)
        return sorted(rows, key=lambda row: (-row["cosine_score"], row["id"]))[:limit]


class MemoryProfiles:
    """Model the repository contract, including generation scoping and CAS."""
    def __init__(self, document=None, signals=()):
        self.document = deepcopy(document)
        self.events = deepcopy(list(signals))
        self.signal_calls = []
        self.cas_calls = []
        self.on_compare = None
        self.next_generation = 1

    def get(self, user_id):
        assert user_id == USER_ID
        return deepcopy(self.document)

    def save(self, user_id, value, vector, model):
        self.next_generation += 1
        version = self.document["profile_version"] + 1 if self.document else 1
        self.document = profile(
            initial=vector,
            preferences=value.model_dump(),
            embedding_model=model,
            profile_version=version,
            profile_generation=f"generation-{self.next_generation}",
        )
        return deepcopy(self.document)

    def record(self, user_id, event, profile_generation=None):
        self.events.append({
            "user_id": user_id,
            **event.model_dump(),
            "received_at": NOW,
            "profile_generation": profile_generation,
        })
        return {"event_id": str(len(self.events)), "received_at": NOW}

    def recent_signals(self, user_id, since, profile_generation):
        self.signal_calls.append((user_id, since, profile_generation))
        return [deepcopy(event) for event in self.events
                if event["received_at"] >= since
                and event.get("profile_generation") == profile_generation]

    def excluded(self, user_id):
        return sorted({event["listing_id"] for event in self.events
                       if event["type"] == "not_interested"})

    def compare_and_update(self, user_id, expected_profile, changes):
        self.cas_calls.append((deepcopy(expected_profile), deepcopy(changes)))
        if self.on_compare is not None:
            return self.on_compare(self, expected_profile, changes)
        if (self.document["profile_version"] != expected_profile["profile_version"]
                or self.document.get("profile_generation") != expected_profile.get("profile_generation")):
            return None
        version = self.document["profile_version"] + 1
        self.document.update(deepcopy(changes))
        self.document["profile_version"] = version
        return deepcopy(self.document)


@pytest.fixture
def make_service(monkeypatch):
    monkeypatch.setattr(service_module, "LocalModels", FakeModels)

    def make(document=None, rows=(), signals=()):
        return service_module.RecommendationService(
            MemoryListings(rows), MemoryProfiles(document, signals))

    return make


@pytest.fixture
def make_client():
    def make(service):
        app = FastAPI()
        app.include_router(router)
        app.dependency_overrides[get_service] = lambda: service
        app.dependency_overrides[get_recommendation_user_id] = lambda: USER_ID
        return TestClient(app)

    return make


def test_normalization_returns_unit_vector_without_mutating_input():
    vector = axis(0)
    vector[0], vector[1] = 3.0, 4.0
    normalized = behavior.normalize_vector(vector)
    assert normalized[:2] == pytest.approx([0.6, 0.8])
    assert sum(value * value for value in normalized) == pytest.approx(1.0)
    assert vector[:2] == [3.0, 4.0]


@pytest.mark.parametrize("vector", [
    None, [], [1.0] * 383, [0.0] * 384,
    [float("nan")] + [0.0] * 383,
    [float("inf")] + [0.0] * 383,
    ["invalid"] + [0.0] * 383,
])
def test_normalization_rejects_invalid_vectors(vector):
    with pytest.raises(ValueError):
        behavior.normalize_vector(vector)


def test_save_and_contact_have_more_influence_than_a_qualified_view():
    result = behavior.build_behavior_profile(axis(0), [
        signal(1, "view", 5_000), signal(2, "save"), signal(3, "contact"),
    ], {1: axis(1), 2: axis(2), 3: axis(3)})
    vector = result["preference_vector"]
    assert vector[3] > vector[2] > vector[1] > 0
    assert vector[2] / vector[1] == pytest.approx(3.0)
    assert vector[3] / vector[1] == pytest.approx(5.0)
    assert result["behavior_listing_count"] == 3
    assert result["behavior_weight"] == 9.0
    assert result["behavior_blend"] == pytest.approx(0.35)
    assert result["behavior_signal_weights"] == {"1": 1.0, "2": 3.0, "3": 5.0}
    assert vector[0] > 0
    assert sqrt(sum(value * value for value in vector)) == pytest.approx(1.0)


def test_repeated_events_use_the_strongest_signal_once_per_listing():
    expected = behavior.build_behavior_profile(axis(0), [signal(1)], {1: axis(1)})
    repeated = behavior.build_behavior_profile(axis(0), [
        signal(1, "view", 60_000), signal(1, "save"), *[signal(1)] * 50,
    ], {1: axis(1)})
    assert repeated == expected
    assert repeated["behavior_weight"] == 5.0
    assert repeated["behavior_listing_count"] == 1
    assert repeated["behavior_blend"] == pytest.approx(0.25)
    assert repeated["behavior_signal_weights"] == {"1": 5.0}


@pytest.mark.parametrize("duration_ms", [None, 0, 4_999])
def test_short_or_unmeasured_views_do_not_change_the_anchor(duration_ms):
    result = behavior.build_behavior_profile(axis(0), [signal(1, "view", duration_ms)], {1: axis(1)})
    assert result["preference_vector"] == axis(0)
    assert result["behavior_listing_count"] == 0
    assert result["behavior_weight"] == 0.0
    assert result["behavior_blend"] == 0.0


def test_missing_invalid_and_excluded_embeddings_do_not_influence_learning():
    result = behavior.build_behavior_profile(axis(0), [signal(i) for i in range(1, 7)], {
        2: [1.0] * 383,
        3: [float("nan")] + [0.0] * 383,
        4: [0.0] * 384,
        5: axis(2),
        6: axis(1),
    }, excluded=[5])
    expected = behavior.build_behavior_profile(axis(0), [signal(6)], {6: axis(1)})
    assert result == expected


def test_negative_feedback_never_becomes_a_positive_signal():
    result = behavior.build_behavior_profile(axis(0), [signal(1, "not_interested")], {1: axis(1)})
    assert result["preference_vector"] == axis(0)
    assert result["behavior_listing_count"] == 0


def test_many_unique_contacts_cannot_replace_the_declared_anchor():
    result = behavior.build_behavior_profile(axis(0), [signal(i) for i in range(1, 101)],
                                             {i: axis(1) for i in range(1, 101)})
    assert result["behavior_blend"] == pytest.approx(0.35)
    assert result["preference_vector"][0] > result["preference_vector"][1] > 0
    assert result["behavior_listing_count"] == 100


def test_opposing_room_vectors_keep_a_valid_declared_anchor():
    opposite = [-value for value in axis(1)]
    result = behavior.build_behavior_profile(axis(0), [signal(1), signal(2)],
                                             {1: axis(1), 2: opposite})
    assert result["preference_vector"] == axis(0)
    assert result["behavior_blend"] == 0.0


def test_record_learns_from_existing_embeddings_and_keeps_the_declared_anchor(make_service):
    service = make_service(profile(), [listing(1, axis(1))])
    result = service.record(USER_ID, InteractionIn(listing_id=1, type="contact"))
    assert result["learning_status"] == "updated"
    assert result["event_learning_reason"] == "eligible"
    assert result["profile_updated"] is True
    assert result["profile_version"] == 2
    assert result["behavior_listing_count"] == 1
    assert service.profiles.document["initial_vector"] == axis(0)
    assert service.profiles.document["preference_vector"][1] > 0
    assert service.models.embed_calls == []
    assert service.listings.embedding_calls == [([1], EMBEDDING_MODEL)]
    assert service.profiles.events[0]["profile_generation"] == "generation-1"


def test_duplicate_contacts_remain_recorded_without_amplifying_the_profile(make_service):
    service = make_service(profile(), [listing(1, axis(1))])
    first = service.record(USER_ID, InteractionIn(listing_id=1, type="contact"))
    vector = deepcopy(service.profiles.document["preference_vector"])
    second = service.record(USER_ID, InteractionIn(listing_id=1, type="contact"))
    assert len(service.profiles.events) == 2
    assert second["event_id"] != first["event_id"]
    assert second["learning_status"] == "unchanged"
    assert second["event_learning_reason"] == "duplicate_signal"
    assert second["profile_updated"] is False
    assert service.profiles.document["profile_version"] == first["profile_version"]
    assert service.profiles.document["preference_vector"] == vector
    assert service.profiles.document["behavior_weight"] == 5.0


def test_no_profile_still_records_the_interaction(make_service):
    service = make_service(rows=[listing(1, axis(1))])
    result = service.record(USER_ID, InteractionIn(listing_id=1, type="save"))
    assert result["learning_status"] == "no_profile"
    assert result["event_learning_reason"] == "no_profile"
    assert result["profile_updated"] is False
    assert len(service.profiles.events) == 1
    assert service.profiles.document is None
    assert service.listings.embedding_calls == []
    assert service.models.embed_calls == []


@pytest.mark.parametrize("duration_ms", [None, 0, 4_999])
def test_record_reports_short_view_without_profile_learning(make_service, duration_ms):
    service = make_service(profile(), [listing(1, axis(1))])
    result = service.record(USER_ID, InteractionIn(listing_id=1, type="view", duration_ms=duration_ms))
    assert result["event_learning_reason"] == "short_view"
    assert result["learning_status"] == "unchanged"
    assert result["profile_updated"] is False
    assert len(service.profiles.events) == 1
    assert service.profiles.document["preference_vector"] == axis(0)
    assert service.profiles.document["behavior_signal_weights"] == {}


@pytest.mark.parametrize("row", [
    listing(1, None),
    listing(1, [1.0] * 383),
    listing(1, axis(1), embedding_model="a-different-model"),
], ids=["missing", "invalid", "incompatible-model"])
def test_record_reports_unavailable_embedding_without_profile_learning(make_service, row):
    service = make_service(profile(), [row])
    result = service.record(USER_ID, InteractionIn(listing_id=1, type="contact"))
    assert result["event_learning_reason"] == "unavailable_embedding"
    assert result["learning_status"] == "unchanged"
    assert result["profile_updated"] is False
    assert len(service.profiles.events) == 1
    assert service.profiles.document["preference_vector"] == axis(0)
    assert service.profiles.document["behavior_signal_weights"] == {}


@pytest.mark.parametrize("event,row,reason", [
    (InteractionIn(listing_id=1, type="view", duration_ms=100), listing(1, axis(1)), "short_view"),
    (InteractionIn(listing_id=1, type="contact"), listing(1, [1.0] * 383), "unavailable_embedding"),
])
def test_legacy_metadata_migration_does_not_claim_the_event_learned(make_service, event, row, reason):
    legacy = profile()
    for key in ("behavior_since", "behavior_listing_count", "behavior_weight", "behavior_blend",
                "behavior_signal_weights", "profile_generation"):
        legacy.pop(key)
    service = make_service(legacy, [row])
    result = service.record(USER_ID, event)
    assert result["profile_updated"] is True
    assert result["learning_status"] == "updated"
    assert result["event_learning_reason"] == reason
    assert service.profiles.document["preference_vector"] == axis(0)
    assert service.profiles.document["behavior_listing_count"] == 0
    assert service.profiles.document["behavior_signal_weights"] == {}
    assert len(service.profiles.events) == 1


@pytest.mark.parametrize("kind,duration_ms", [("view", 5_000), ("save", None), ("contact", None)])
def test_weaker_and_equal_events_report_duplicate_signal_after_contact(make_service, kind, duration_ms):
    service = make_service(profile(), [listing(1, axis(1))])
    service.record(USER_ID, InteractionIn(listing_id=1, type="contact"))
    before = deepcopy(service.profiles.document)
    result = service.record(USER_ID, InteractionIn(listing_id=1, type=kind, duration_ms=duration_ms))
    assert result["event_learning_reason"] == "duplicate_signal"
    assert result["profile_updated"] is False
    assert service.profiles.document == before
    assert len(service.profiles.events) == 2


def test_stronger_event_is_eligible_without_counting_the_listing_twice(make_service):
    service = make_service(profile(), [listing(1, axis(1))])
    saved = service.record(USER_ID, InteractionIn(listing_id=1, type="save"))
    assert saved["event_learning_reason"] == "eligible"
    contacted = service.record(USER_ID, InteractionIn(listing_id=1, type="contact"))
    assert contacted["event_learning_reason"] == "eligible"
    assert contacted["profile_updated"] is True
    assert contacted["behavior_listing_count"] == 1
    assert service.profiles.document["behavior_weight"] == 5.0
    assert service.profiles.document["behavior_signal_weights"] == {"1": 5.0}


def test_previously_excluded_listing_never_learns_from_positive_events(make_service):
    service = make_service(profile(), [listing(1, axis(1))], [signal(1, "not_interested")])
    result = service.record(USER_ID, InteractionIn(listing_id=1, type="contact"))
    assert result["event_learning_reason"] == "excluded"
    assert result["profile_updated"] is False
    assert service.profiles.document["preference_vector"] == axis(0)
    assert service.profiles.document["behavior_signal_weights"] == {}
    assert len(service.profiles.events) == 2


def test_incompatible_model_and_invalid_listing_vectors_are_ignored(make_service):
    service = make_service(profile(), [
        listing(1, axis(1), embedding_model="a-different-model"),
        listing(2, [1.0] * 383),
        listing(3, None),
    ], [signal(1), signal(2), signal(3)])
    refreshed, changed = service.refresh_profile(USER_ID)
    assert changed is False
    assert refreshed["preference_vector"] == axis(0)
    assert refreshed["behavior_listing_count"] == 0
    assert service.listings.embedding_calls[0][1] == EMBEDDING_MODEL


@pytest.mark.parametrize("current_vector", [
    None, [], [1.0] * 383, [0.0] * 384,
    [float("nan")] + [0.0] * 383,
    [float("inf")] + [0.0] * 383,
    ["invalid"] + [0.0] * 383,
], ids=["missing", "empty", "wrong-dimension", "zero", "nan", "infinity", "not-numeric"])
def test_malformed_learned_vector_is_rebuilt_from_the_valid_initial_anchor(make_service, current_vector):
    service = make_service(profile(preference_vector=current_vector))
    refreshed, changed = service.refresh_profile(USER_ID)
    assert changed is True
    assert refreshed["preference_vector"] == axis(0)
    assert refreshed["initial_vector"] == axis(0)
    assert refreshed["profile_version"] == 2
    assert refreshed["behavior_listing_count"] == 0
    assert service.models.embed_calls == []


def test_saved_preferences_reset_learning_and_scope_out_earlier_events(make_service):
    service = make_service(profile(), [listing(1, axis(1))], [signal(1)])
    learned, _ = service.refresh_profile(USER_ID)
    assert learned["behavior_listing_count"] == 1
    service.models.vector = axis(3)
    saved = service.save_preferences(USER_ID, preferences(max_price=1_500_000, district="Cai Rang"))
    refreshed, changed = service.refresh_profile(USER_ID)
    assert saved["initial_vector"] == axis(3)
    assert refreshed["preference_vector"] == axis(3)
    assert refreshed["behavior_listing_count"] == 0
    assert changed is False
    assert refreshed["profile_generation"] != "generation-1"
    assert refreshed["profile_version"] > learned["profile_version"]
    assert refreshed["behavior_signal_weights"] == {}


def test_for_you_keeps_price_and_district_constraints_and_negative_exclusions(make_service):
    service = make_service(profile(), [
        listing(1, axis(1)), listing(2, axis(1), price=2_000_001),
        listing(3, axis(1), district="Cai Rang"), listing(4, axis(1)),
    ], [signal(1), signal(4), signal(4, "not_interested")])
    result = service.for_you(USER_ID, top_k=10, rerank=False)
    assert [item.listing_id for item in result.items] == [1]
    query = service.listings.search_calls[-1]
    assert query["preferences"] == preferences().model_dump()
    assert query["excluded"] == [4]
    assert query["model"] == EMBEDDING_MODEL
    assert service.profiles.document["initial_vector"] == axis(0)
    assert service.profiles.document["behavior_listing_count"] == 1


def test_cas_conflict_retries_with_the_latest_anchor_and_generation(make_service):
    service = make_service(profile(), [listing(1, axis(1)), listing(2, axis(2))], [signal(1)])

    def replace_preferences(repo, expected, changes):
        repo.document = profile(
            initial=axis(3), profile_version=2, profile_generation="generation-new",
            preferences=preferences(max_price=1_500_000).model_dump())
        repo.events.append(signal(2, generation="generation-new"))
        repo.on_compare = None
        return None

    service.profiles.on_compare = replace_preferences
    refreshed, changed = service.refresh_profile(USER_ID)
    assert changed is True
    assert len(service.profiles.cas_calls) == 2
    assert [call[2] for call in service.profiles.signal_calls] == ["generation-1", "generation-new"]
    assert refreshed["profile_generation"] == "generation-new"
    assert refreshed["initial_vector"] == axis(3)
    assert refreshed["preferences"]["max_price"] == 1_500_000
    assert refreshed["preference_vector"][0:2] == [0.0, 0.0]
    assert refreshed["preference_vector"][2] > 0
    assert refreshed["preference_vector"][3] > 0


def test_refresh_stops_after_three_conflicts(make_service):
    service = make_service(profile(), [listing(1, axis(1))], [signal(1)])
    service.profiles.on_compare = lambda repo, expected, changes: None
    with pytest.raises(HTTPException) as failure:
        service.refresh_profile(USER_ID)
    assert failure.value.status_code == 409
    assert len(service.profiles.cas_calls) == 3


def test_record_reports_stale_generation_when_preferences_change_during_learning(make_service):
    service = make_service(profile(), [listing(1, axis(1))])

    def reset_preferences(repo, expected, changes):
        repo.document = profile(initial=axis(3), profile_version=2, profile_generation="generation-new")
        repo.on_compare = None
        return None

    service.profiles.on_compare = reset_preferences
    result = service.record(USER_ID, InteractionIn(listing_id=1, type="contact"))
    assert result["event_learning_reason"] == "stale_generation"
    assert result["profile_updated"] is False
    assert result["learning_status"] == "unchanged"
    assert service.profiles.document["initial_vector"] == axis(3)
    assert service.profiles.document["preference_vector"] == axis(3)
    assert service.profiles.document["behavior_signal_weights"] == {}
    assert service.profiles.events[0]["profile_generation"] == "generation-1"
    assert [call[2] for call in service.profiles.signal_calls] == ["generation-1", "generation-new"]


def test_record_reports_pending_learning_when_cas_retries_are_exhausted(make_service):
    service = make_service(profile(), [listing(1, axis(1))])
    service.profiles.on_compare = lambda repo, expected, changes: None
    result = service.record(USER_ID, InteractionIn(listing_id=1, type="save"))
    assert result["event_id"] == "1"
    assert result["learning_status"] == "pending"
    assert result["event_learning_reason"] == "pending"
    assert result["profile_updated"] is False
    assert result["learning_warning"]
    assert len(service.profiles.events) == 1
    assert len(service.profiles.cas_calls) == 3


def test_pending_durable_event_is_repaired_on_the_next_profile_read(make_service):
    service = make_service(profile(), [listing(1, axis(1))])
    service.profiles.on_compare = lambda repo, expected, changes: None
    event = service.record(USER_ID, InteractionIn(listing_id=1, type="contact"))
    assert event["learning_status"] == "pending"
    assert event["event_learning_reason"] == "pending"
    service.profiles.on_compare = None
    repaired = service.profile(USER_ID)
    assert repaired["behavior_listing_count"] == 1
    assert repaired["preference_vector"][1] > 0
    assert repaired["initial_vector"] == axis(0)
    assert len(service.profiles.events) == 1


def test_reranking_requires_explicit_opt_in_after_behavior_learning(make_service):
    service = make_service(profile(), [listing(1, axis(1)), listing(2, axis(0))], [signal(1)])
    ordinary = service.for_you(USER_ID, top_k=2, rerank=False)
    assert ordinary.reranker_model is None
    assert service.models.rerank_calls == []
    reranked = service.for_you(USER_ID, top_k=2, rerank=True)
    assert reranked.reranker_model == RERANKER_MODEL
    assert len(service.models.rerank_calls) == 1
    assert service.listings.search_calls[-1]["limit"] == 50
    assert len(reranked.warnings) > len(ordinary.warnings)
    assert [item.listing_id for item in reranked.items] == list(reversed([item.listing_id for item in ordinary.items]))


def test_api_saved_profile_interaction_and_feedback_lifecycle(make_service, make_client):
    service = make_service(rows=[listing(1, axis(1)), listing(2, axis(0))])
    client = make_client(service)
    saved = client.put("/recommend/preferences", json=preferences().model_dump())
    assert saved.status_code == 200
    assert saved.json()["preferences"] == preferences().model_dump()
    assert "initial_vector" not in saved.json()
    assert "preference_vector" not in saved.json()
    assert "behavior_signal_weights" not in saved.json()
    event = client.post("/recommend/interactions", json={"listing_id": 1, "type": "contact"})
    assert event.status_code == 201
    assert event.json()["learning_status"] == "updated"
    assert event.json()["event_learning_reason"] == "eligible"
    assert event.json()["profile_updated"] is True
    assert event.json()["behavior_listing_count"] == 1
    recommended = client.get("/recommend/for-you")
    assert recommended.status_code == 200
    assert service.listings.search_calls[-1]["vector"][1] > 0
    duplicate = client.post("/recommend/interactions", json={"listing_id": 1, "type": "contact"})
    assert duplicate.status_code == 201
    assert duplicate.json()["event_learning_reason"] == "duplicate_signal"
    assert duplicate.json()["profile_updated"] is False
    rejected = client.post("/recommend/interactions", json={"listing_id": 1, "type": "not_interested"})
    assert rejected.status_code == 201
    assert rejected.json()["event_learning_reason"] == "excluded"
    result = client.get("/recommend/for-you")
    assert result.status_code == 200
    assert [item["listing_id"] for item in result.json()["items"]] == [2]
    current = client.get("/recommend/preferences")
    assert current.status_code == 200
    assert "initial_vector" not in current.json()
    assert "preference_vector" not in current.json()
    assert "behavior_signal_weights" not in current.json()


def test_api_unknown_listing_and_client_supplied_identity_are_not_recorded(make_service, make_client):
    service = make_service(profile(), [listing(1, axis(1))])
    client = make_client(service)
    assert client.post("/recommend/interactions", json={"listing_id": 999, "type": "save"}).status_code == 404
    assert client.post("/recommend/interactions", json={
        "listing_id": 1, "type": "save", "user_id": "postgres:someone-else",
    }).status_code == 422
    assert service.profiles.events == []


def test_api_can_record_feedback_before_preferences_are_saved(make_service, make_client):
    service = make_service(rows=[listing(1, axis(1))])
    client = make_client(service)
    result = client.post("/recommend/interactions", json={"listing_id": 1, "type": "save"})
    assert result.status_code == 201
    assert result.json()["learning_status"] == "no_profile"
    assert result.json()["event_learning_reason"] == "no_profile"
    assert client.get("/recommend/for-you").status_code == 404
    assert len(service.profiles.events) == 1


def test_api_preserves_durable_success_when_event_reason_lookup_fails(make_service, make_client, monkeypatch):
    service = make_service(profile(), [listing(1, axis(1))])
    excluded_calls = []
    read_excluded = service.profiles.excluded

    def unavailable_after_refresh(user_id):
        excluded_calls.append(user_id)
        if len(excluded_calls) == 1:
            return read_excluded(user_id)
        raise HTTPException(503, "Reason lookup temporarily unavailable")

    monkeypatch.setattr(service.profiles, "excluded", unavailable_after_refresh)
    result = make_client(service).post("/recommend/interactions", json={"listing_id": 1, "type": "contact"})
    assert result.status_code == 201
    payload = result.json()
    assert payload["event_id"] == "1"
    assert payload["profile_updated"] is True
    assert payload["learning_status"] == "updated"
    assert payload["event_learning_reason"] == "pending"
    assert payload["learning_warning"] == "Reason lookup temporarily unavailable"
    assert payload["profile_version"] == 2
    assert payload["behavior_listing_count"] == 1
    assert excluded_calls == [USER_ID, USER_ID]
    assert len(service.profiles.events) == 1
    assert service.profiles.document["preference_vector"][1] > 0
    assert service.profiles.document["initial_vector"] == axis(0)
    assert service.profiles.document["behavior_signal_weights"] == {"1": 5.0}


def test_public_preview_needs_no_profile_storage_and_defaults_to_cosine(make_service, make_client):
    service = make_service(rows=[listing(1, axis(0))])

    def unexpected_profile_access(user_id):
        pytest.fail("Public preview must not access saved profile storage")

    service.profiles.get = unexpected_profile_access
    result = make_client(service).post("/recommend/preview", json=preferences().model_dump())
    assert result.status_code == 200
    assert result.json()["reranker_model"] is None
    assert service.models.rerank_calls == []
    assert len(service.models.embed_calls) == 1
    assert service.profiles.events == []
