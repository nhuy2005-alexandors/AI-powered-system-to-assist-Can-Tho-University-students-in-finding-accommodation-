"""Real SQL and HTTP integration in an explicitly isolated test database."""
import os
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text

from app.auth import get_current_user
from app.auth.schemas import UserOut
from app.reports.repo import ReportRepository
from app.reports.router import get_service as report_service, router as reports_router
from app.reports.service import ReportService
from app.reviews.repo import ReviewRepository
from app.reviews.router import get_service as review_service, router as reviews_router
from app.reviews.service import ReviewService


@pytest.fixture
def feedback():
    url = os.getenv("FEEDBACK_TEST_DATABASE_URL")
    if not url:
        pytest.skip("Set FEEDBACK_TEST_DATABASE_URL to an isolated PostgreSQL database")
    assert url.rsplit("/", 1)[-1].endswith("_test"), "Refuse application database"
    engine = create_engine(url)
    users = []
    with engine.begin() as conn:
        for role in ("user", "user", "admin"):
            users.append(conn.execute(text(
                "INSERT INTO users (email,name,role) VALUES (:email,'Feedback Test',:role) RETURNING id"
            ), {"email": f"{uuid4()}@example.test", "role": role}).scalar_one())
        listing_id = conn.execute(text(
            "INSERT INTO aggregated_listings (title,source,posted_by) "
            "VALUES ('Feedback integration room','user',:owner) RETURNING id"
        ), {"owner": users[1]}).scalar_one()
    app = FastAPI()
    app.include_router(reports_router)
    app.include_router(reviews_router)
    app.dependency_overrides[report_service] = lambda: ReportService(ReportRepository(engine))
    app.dependency_overrides[review_service] = lambda: ReviewService(ReviewRepository(engine))
    student = UserOut(id=users[0], email="student@example.test", role="user")
    owner = UserOut(id=users[1], email="owner@example.test", role="user")
    admin = UserOut(id=users[2], email="admin@example.test", role="admin")
    app.dependency_overrides[get_current_user] = lambda: student
    try:
        with TestClient(app) as client:
            yield client, app, engine, listing_id, student, owner, admin
    finally:
        with engine.begin() as conn:
            conn.execute(text("DELETE FROM aggregated_listings WHERE id=:id"), {"id": listing_id})
            for user_id in users:
                conn.execute(text("DELETE FROM users WHERE id=:id"), {"id": user_id})
        engine.dispose()


def test_report_duplicate_auth_and_manual_moderation(feedback):
    client, app, engine, listing, student, owner, admin = feedback
    endpoint = f"/listings/{listing}/report"
    assert client.post(endpoint, json={"reason": "invalid"}).status_code == 422
    app.dependency_overrides[get_current_user] = lambda: owner
    assert client.post(endpoint, json={"reason": "scam"}).status_code == 400
    app.dependency_overrides[get_current_user] = lambda: student
    created = client.post(endpoint, json={"reason": "scam", "note": "  Yêu cầu chuyển cọc trước  "})
    assert created.status_code == 201, created.text
    assert created.json()["note"] == "Yêu cầu chuyển cọc trước"
    assert client.post(endpoint, json={"reason": "scam"}).status_code == 409
    with engine.connect() as conn:
        row = conn.execute(text("SELECT status::text, risk_score FROM aggregated_listings WHERE id=:id"), {"id": listing}).one()
    assert row == ("active", 0), "A pending report must not auto-label a listing"
    assert client.get("/admin/reports").status_code == 403
    app.dependency_overrides[get_current_user] = lambda: admin
    queue = client.get("/admin/reports")
    assert queue.status_code == 200, queue.text
    assert any(item["id"] == created.json()["id"] for item in queue.json()["items"])
    report_id = created.json()["id"]
    result = client.patch(f"/admin/reports/{report_id}", json={"action": "flag", "note": "Cần xác minh"})
    assert result.status_code == 200, result.text
    assert result.json()["listing_status"] == "flagged"
    assert result.json()["risk_score"] is None
    assert client.patch(f"/admin/reports/{report_id}", json={"action": "hide"}).status_code == 409
    with engine.connect() as conn:
        audit = conn.execute(text("SELECT reviewed_by, reviewed_at, resolution_note FROM reports WHERE id=:id"), {"id": report_id}).one()
    assert audit[0] == admin.id and audit[1] is not None and audit[2] == "Cần xác minh"
    assert client.get("/admin/summary").status_code == 200
    assert client.get("/admin/listings?q=Feedback").status_code == 200
    assert client.get("/admin/users?q=example.test").status_code == 200


def test_dismiss_preserves_hidden_listing(feedback):
    client, app, engine, listing, student, owner, admin = feedback
    created = client.post(f"/listings/{listing}/report", json={"reason": "expired"}).json()
    with engine.begin() as conn:
        conn.execute(text("UPDATE aggregated_listings SET status='hidden' WHERE id=:id"), {"id": listing})
    app.dependency_overrides[get_current_user] = lambda: admin
    result = client.patch(f"/admin/reports/{created['id']}", json={"action": "dismiss"})
    assert result.status_code == 200, result.text
    assert result.json()["listing_status"] == "hidden"
    assert client.get("/admin/reports?status=dismissed").json()["items"][0]["status"] == "dismissed"


def test_review_unique_summary_and_hide(feedback):
    client, app, engine, listing, student, owner, admin = feedback
    endpoint = f"/listings/{listing}/reviews"
    positive = {"rating": 4, "comment": "Phòng sạch sẽ, giá hợp lý và chủ nhà rất thân thiện"}
    negative = {"rating": 1, "comment": "Phòng rất bẩn, chủ trọ thu phí vô lý và không trả tiền cọc"}
    created = client.post(endpoint, json=negative)
    assert created.status_code == 201, created.text
    assert created.json()["is_flagged"] is True
    assert client.post(endpoint, json=positive).status_code == 409
    app.dependency_overrides[get_current_user] = lambda: owner
    assert client.post(endpoint, json=positive).status_code == 400
    app.dependency_overrides[get_current_user] = lambda: admin
    assert client.post(endpoint, json=positive).status_code == 201
    summary = client.get(endpoint).json()["summary"]
    assert summary["total"] == 2 and summary["average_rating"] == 2.5
    queue = client.get("/admin/reviews/flagged")
    assert queue.status_code == 200 and queue.json()["total"] >= 1
    hidden = client.patch(f"/admin/reviews/{created.json()['id']}", json={"action": "hide"})
    assert hidden.status_code == 200
    summary = client.get(endpoint).json()["summary"]
    assert summary["total"] == 1 and summary["average_rating"] == 4
    app.dependency_overrides[get_current_user] = lambda: student
    assert client.post(endpoint, json=positive).status_code == 409


def test_report_anonymous_and_missing_listing(feedback):
    client, app, _, listing, *_ = feedback
    assert client.post("/listings/2147483647/report", json={"reason": "scam"}).status_code == 404
    app.dependency_overrides.pop(get_current_user)
    assert client.post(f"/listings/{listing}/report", json={"reason": "scam"}).status_code == 403
    assert client.get("/admin/reports").status_code == 403
