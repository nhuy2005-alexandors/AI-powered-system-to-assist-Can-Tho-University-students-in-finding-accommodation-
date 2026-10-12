"""HTTP review contracts with the real service/model and an in-memory repository."""

from datetime import datetime, timezone

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError

from app.auth import get_current_user
from app.auth.schemas import UserOut
from app.reviews.router import get_service, router
from app.reviews.schemas import AdminReviewItem, ReviewOut
from app.reviews.sentiment import VietnameseReviewSentimentModel
from app.reviews.service import ReviewService


NEGATIVE = "Phòng rất bẩn, chủ trọ thu phí vô lý và không trả tiền cọc."
POSITIVE = "Phòng sạch sẽ, giá hợp lý và chủ nhà rất thân thiện"
USER = UserOut(id=10, email="student@example.com", name="Student", role="user")
ADMIN = UserOut(id=1, email="admin@example.com", name="Admin", role="admin")


class MemoryReviews:
    def __init__(self):
        self.listing = {"id": 7, "posted_by": 20, "status": "active"}
        self.rows = {}

    def get_listing(self, listing_id):
        return self.listing if listing_id == 7 else None

    def create(self, listing_id, user_id, rating, comment, sentiment_label,
               negative_score, moderation_status, model_version):
        if any(r.listing_id == listing_id and r.user_id == user_id
               for r in self.rows.values()):
            raise IntegrityError("insert", {}, Exception("duplicate"))
        now = datetime.now(timezone.utc)
        row = ReviewOut(
            id=len(self.rows) + 1, listing_id=listing_id, user_id=user_id,
            author_name="Student", rating=rating, comment=comment,
            sentiment_label=sentiment_label, negative_score=negative_score,
            moderation_status=moderation_status,
            is_flagged=moderation_status == "flagged", model_version=model_version,
            created_at=now, updated_at=now,
        )
        self.rows[row.id] = row
        return row

    def flagged(self, limit, offset):
        rows = [AdminReviewItem(**r.model_dump(), listing_title="Test room")
                for r in self.rows.values() if r.moderation_status == "flagged"]
        return len(rows), rows[offset:offset + limit]

    def moderate(self, review_id, status):
        row = self.rows.get(review_id)
        if row is None:
            return None
        row = row.model_copy(update={
            "moderation_status": status, "is_flagged": status == "flagged",
        })
        self.rows[review_id] = row
        return row


@pytest.fixture
def api():
    app = FastAPI()
    app.include_router(router)
    repo = MemoryReviews()
    service = ReviewService(repo, VietnameseReviewSentimentModel())
    app.dependency_overrides[get_service] = lambda: service
    app.dependency_overrides[get_current_user] = lambda: USER
    with TestClient(app) as client:
        yield client, app, repo


@pytest.mark.parametrize("comment,label,flagged", [
    (NEGATIVE, "negative", True),
    (POSITIVE, "positive", False),
    ("Mình muốn hỏi phòng còn trống không?", "neutral", False),
])
@pytest.mark.parametrize("rating", [1, 5])
def test_http_sentiment_depends_on_comment_not_stars(api, comment, label, flagged, rating):
    client, _, repo = api
    response = client.post("/listings/7/reviews", json={
        "rating": rating, "comment": f"  {comment}  ",
    })
    assert response.status_code == 201, response.text
    data = response.json()
    assert data["sentiment_label"] == label
    assert data["is_flagged"] is flagged
    assert data["moderation_status"] == ("flagged" if flagged else "published")
    assert data["comment"] == comment
    assert repo.rows[data["id"]].comment == comment


@pytest.mark.parametrize("action,status", [("approve", "published"), ("hide", "hidden")])
def test_admin_can_find_and_resolve_flagged_review(api, action, status):
    client, app, _ = api
    created = client.post("/listings/7/reviews", json={"rating": 1, "comment": NEGATIVE})
    assert created.status_code == 201
    review_id = created.json()["id"]
    assert client.get("/admin/reviews/flagged").status_code == 403
    assert client.patch(f"/admin/reviews/{review_id}", json={"action": action}).status_code == 403
    app.dependency_overrides[get_current_user] = lambda: ADMIN
    queue = client.get("/admin/reviews/flagged")
    assert queue.status_code == 200
    assert queue.json()["total"] == 1
    assert queue.json()["items"][0]["id"] == review_id
    resolved = client.patch(f"/admin/reviews/{review_id}", json={"action": action})
    assert resolved.status_code == 200, resolved.text
    assert resolved.json()["moderation_status"] == status
    assert resolved.json()["is_flagged"] is False
    assert client.get("/admin/reviews/flagged").json() == {"total": 0, "items": []}


@pytest.mark.parametrize("body", [
    {"rating": 0, "comment": NEGATIVE},
    {"rating": 6, "comment": NEGATIVE},
    {"rating": 1, "comment": "ngắn"},
    {"rating": 1, "comment": " " * 10},
    {"rating": 1, "comment": "a" * 2001},
    {"rating": 1},
])
def test_invalid_review_is_rejected_without_write(api, body):
    client, _, repo = api
    assert client.post("/listings/7/reviews", json=body).status_code == 422
    assert repo.rows == {}


def test_anonymous_requests_are_rejected(api):
    client, app, repo = api
    del app.dependency_overrides[get_current_user]
    assert client.post("/listings/7/reviews", json={"rating": 1, "comment": NEGATIVE}).status_code == 403
    assert client.get("/admin/reviews/flagged").status_code == 403
    assert client.patch("/admin/reviews/1", json={"action": "hide"}).status_code == 403
    assert repo.rows == {}


def test_duplicate_and_missing_listing(api):
    client, _, repo = api
    body = {"rating": 1, "comment": NEGATIVE}
    assert client.post("/listings/999/reviews", json=body).status_code == 404
    assert client.post("/listings/7/reviews", json=body).status_code == 201
    assert client.post("/listings/7/reviews", json=body).status_code == 409
    assert len(repo.rows) == 1


@pytest.mark.parametrize("status", ["hidden", "expired"])
def test_unavailable_listing_rejects_review(api, status):
    client, _, repo = api
    repo.listing["status"] = status
    assert client.post("/listings/7/reviews", json={"rating": 1, "comment": NEGATIVE}).status_code == 409
    assert repo.rows == {}


def test_admin_invalid_action_and_missing_review(api):
    client, app, _ = api
    app.dependency_overrides[get_current_user] = lambda: ADMIN
    assert client.patch("/admin/reviews/999", json={"action": "delete"}).status_code == 422
    assert client.patch("/admin/reviews/999", json={"action": "hide"}).status_code == 404


@pytest.mark.xfail(strict=True, reason="vi-review-nb-v1 misses negative Vietnamese without accents")
def test_negative_comment_without_accents_should_be_flagged(api):
    client, _, _ = api
    response = client.post("/listings/7/reviews", json={
        "rating": 1, "comment": "Phong rat ban, chu tro lua dao khong tra tien coc",
    })
    assert response.status_code == 201
    assert response.json()["is_flagged"] is True


@pytest.mark.xfail(strict=True, reason="vi-review-nb-v1 misreads negated negative phrases")
def test_negated_negative_comment_should_not_be_flagged(api):
    client, _, _ = api
    response = client.post("/listings/7/reviews", json={
        "rating": 5, "comment": "Phòng không bẩn, chủ trọ không lừa đảo",
    })
    assert response.status_code == 201
    assert response.json()["is_flagged"] is False
