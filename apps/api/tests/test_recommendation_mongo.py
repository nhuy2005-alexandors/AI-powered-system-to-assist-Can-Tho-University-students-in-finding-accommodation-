"""Mongo integration tests in a private temporary database, with no ML downloads.

Set RECOMMENDATION_TEST_MONGO_URI to run these against a local MongoDB.
"""
import os
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from app.room_service.recommendation.models import EMBEDDING_MODEL
from app.room_service.recommendation.repo import ProfileRepository
from app.room_service.recommendation.schemas import InteractionIn, Preferences
from app.room_service.recommendation.service import RecommendationService


def axis(index):
    vector = [0.0] * 384
    vector[index] = 1.0
    return vector


@pytest.fixture
def mongo_profiles():
    uri = os.environ.get("RECOMMENDATION_TEST_MONGO_URI")
    if not uri:
        pytest.skip("Set RECOMMENDATION_TEST_MONGO_URI for local Mongo integration tests")
    database = "nckh_recommendation_test_" + uuid4().hex
    repo = ProfileRepository(uri, database)
    repo.db()
    try:
        yield repo
    finally:
        # Only the database created by this fixture is removed.
        assert database.startswith("nckh_recommendation_test_")
        repo.client.drop_database(database)
        repo.close()


class Listings:
    def exists(self, listing_id):
        return listing_id in (1, 2)

    def embeddings(self, listing_ids, model):
        assert model == EMBEDDING_MODEL
        return {listing_id: axis(listing_id) for listing_id in listing_ids}


class Models:
    def embed(self, preferences):
        return axis(0)


def make_service(profiles):
    service = RecommendationService(Listings(), profiles)
    service.models = Models()
    return service


def needs():
    return Preferences(needs="Phòng gần trường", max_price=3_000_000)


def test_mongo_event_learning_dedup_upgrade_and_exclusion(mongo_profiles):
    service = make_service(mongo_profiles)
    user = "test:user"
    saved = service.save_preferences(user, needs())
    first = service.record(user, InteractionIn(listing_id=1, type="save"))
    learned = mongo_profiles.get(user)
    assert first["event_learning_reason"] == "eligible"
    assert first["profile_updated"] is True
    assert learned["initial_vector"] == saved["initial_vector"] == axis(0)
    assert learned["preference_vector"][1] > 0
    assert learned["behavior_weight"] == 3.0

    duplicate = service.record(user, InteractionIn(listing_id=1, type="save"))
    assert duplicate["event_learning_reason"] == "duplicate_signal"
    assert duplicate["profile_updated"] is False
    assert mongo_profiles.get(user)["profile_version"] == learned["profile_version"]
    assert mongo_profiles.db().recommendation_interactions.count_documents({"user_id": user}) == 2

    upgraded = service.record(user, InteractionIn(listing_id=1, type="contact"))
    assert upgraded["profile_updated"] is True
    assert mongo_profiles.get(user)["behavior_weight"] == 5.0
    ignored = service.record(user, InteractionIn(listing_id=2, type="view", duration_ms=4_999))
    assert ignored["event_learning_reason"] == "short_view"
    assert ignored["profile_updated"] is False
    rejected = service.record(user, InteractionIn(listing_id=1, type="not_interested"))
    assert rejected["event_learning_reason"] == "excluded"
    assert service.profile(user)["preference_vector"] == axis(0)
    assert mongo_profiles.excluded(user) == [1]


def test_mongo_preference_reset_rejects_old_generation_and_stale_cas(mongo_profiles):
    user = "test:user"
    old = mongo_profiles.save(user, needs(), axis(0), EMBEDDING_MODEL)
    reset = mongo_profiles.save(user, needs(), axis(2), EMBEDDING_MODEL)
    assert reset["profile_version"] > old["profile_version"]
    assert reset["profile_generation"] != old["profile_generation"]
    stale = mongo_profiles.compare_and_update(user, old, {"preference_vector": axis(1)})
    assert stale is None
    mongo_profiles.record(user, InteractionIn(listing_id=1, type="contact"), old["profile_generation"])
    current, changed = make_service(mongo_profiles).refresh_profile(user)
    assert changed is False
    assert current["initial_vector"] == current["preference_vector"] == axis(2)
    assert current["behavior_listing_count"] == 0


def test_mongo_legacy_profile_learns_and_remains_stable_on_reads(mongo_profiles):
    user = "test:legacy"
    now = datetime.now(timezone.utc)
    mongo_profiles.db().recommendation_profiles.insert_one({
        "user_id": user, "preferences": needs().model_dump(), "embedding_model": EMBEDDING_MODEL,
        "initial_vector": axis(0), "preference_vector": axis(0), "profile_version": 1,
        "created_at": now - timedelta(days=1), "updated_at": now - timedelta(minutes=1),
    })
    # Existing events have no profile_generation field.
    mongo_profiles.db().recommendation_interactions.insert_one({
        "user_id": user, "listing_id": 1, "type": "save", "received_at": now,
    })
    service = make_service(mongo_profiles)
    first, changed = service.refresh_profile(user)
    assert changed is True
    assert first["behavior_listing_count"] == 1
    second, changed = service.refresh_profile(user)
    assert changed is False
    assert second["profile_version"] == first["profile_version"]
    assert second["preference_vector"] == first["preference_vector"]


def test_mongo_history_is_scoped_to_user_generation_and_time(mongo_profiles):
    now = datetime.now(timezone.utc)
    documents = [
        {"user_id": "test:a", "profile_generation": "g", "listing_id": 1, "type": "save", "received_at": now},
        {"user_id": "test:b", "profile_generation": "g", "listing_id": 2, "type": "contact", "received_at": now},
        {"user_id": "test:a", "profile_generation": "old", "listing_id": 2, "type": "save", "received_at": now},
        {"user_id": "test:a", "profile_generation": "g", "listing_id": 2, "type": "contact",
         "received_at": now - timedelta(days=31)},
    ]
    mongo_profiles.db().recommendation_interactions.insert_many(documents)
    signals = mongo_profiles.recent_signals("test:a", now - timedelta(days=60), "g")
    assert signals == [{"listing_id": 1, "type": "save", "duration_ms": None}]
