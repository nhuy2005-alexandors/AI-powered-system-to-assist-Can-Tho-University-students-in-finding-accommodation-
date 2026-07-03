"""E2E tests cho UGC listing CRUD endpoints (FR-3.1/3.2/3.3).

Chạy với Postgres thật (DATABASE_URL trỏ vào docker network `db`), không mock DB.
Mỗi test tự đăng ký user mới (email random) để tránh đụng độ 409 giữa các lần chạy.
"""
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import text

from app.main import app, engine

client = TestClient(app)


def _register() -> dict:
    """Đăng ký user mới (email random) -> {headers, user_id}."""
    email = f"crud_{uuid4().hex[:8]}@example.com"
    r = client.post("/auth/register", json={"email": email, "password": "testpass123"})
    assert r.status_code == 201, r.text
    token = r.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    me = client.get("/auth/me", headers=headers)
    assert me.status_code == 200, me.text
    return {"email": email, "headers": headers, "user_id": me.json()["id"]}


def _listing_payload(**overrides) -> dict:
    payload = {
        "title": f"Phong tro test {uuid4().hex[:6]}",
        "price": 2000000,
        "area": 25.5,
        "address": "Xuan Khanh, Ninh Kieu, Can Tho",
        "district": "Ninh Kieu",
    }
    payload.update(overrides)
    return payload


def test_create_listing_persists_with_owner():
    user = _register()
    payload = _listing_payload()

    r = client.post("/listings", json=payload, headers=user["headers"])
    assert r.status_code == 201, r.text
    body = r.json()
    assert "id" in body
    assert body["title"] == payload["title"]
    assert body["price"] == payload["price"]
    assert body["source"] == "user"

    got = client.get(f"/listings/{body['id']}")
    assert got.status_code == 200, got.text
    got_body = got.json()
    assert got_body["title"] == payload["title"]
    assert got_body["district"] == payload["district"]

    # xác nhận posted_by qua DB trực tiếp (ListingOut không expose posted_by)
    with engine.connect() as conn:
        row = conn.execute(
            text("SELECT posted_by, status FROM aggregated_listings WHERE id = :id"),
            {"id": body["id"]},
        ).mappings().first()
    assert row is not None
    assert row["posted_by"] == user["user_id"]
    assert row["status"] == "active"


def test_create_listing_requires_auth():
    r = client.post("/listings", json=_listing_payload())
    # HTTPBearer(auto_error=True) trả 403 khi thiếu header Authorization (không phải 401)
    assert r.status_code == 403, r.text


def test_update_own_listing():
    user = _register()
    created = client.post("/listings", json=_listing_payload(), headers=user["headers"])
    assert created.status_code == 201, created.text
    listing_id = created.json()["id"]

    new_title = f"Updated title {uuid4().hex[:6]}"
    r = client.put(
        f"/listings/{listing_id}",
        json={"title": new_title, "price": 3000000},
        headers=user["headers"],
    )
    assert r.status_code == 200, r.text
    assert r.json()["title"] == new_title
    assert r.json()["price"] == 3000000

    got = client.get(f"/listings/{listing_id}")
    assert got.status_code == 200, got.text
    assert got.json()["title"] == new_title
    assert got.json()["price"] == 3000000


def test_update_other_users_listing_forbidden():
    user_a = _register()
    user_b = _register()

    created = client.post("/listings", json=_listing_payload(), headers=user_a["headers"])
    assert created.status_code == 201, created.text
    listing_id = created.json()["id"]

    r = client.put(
        f"/listings/{listing_id}",
        json={"title": "hijacked"},
        headers=user_b["headers"],
    )
    assert r.status_code == 403, r.text


def test_update_missing_listing_404():
    user = _register()
    r = client.put(
        "/listings/999999999",
        json={"title": "no such listing"},
        headers=user["headers"],
    )
    assert r.status_code == 404, r.text


def test_delete_own_listing_hides_it():
    user = _register()
    created = client.post("/listings", json=_listing_payload(), headers=user["headers"])
    assert created.status_code == 201, created.text
    listing_id = created.json()["id"]

    r = client.delete(f"/listings/{listing_id}", headers=user["headers"])
    assert r.status_code == 204, r.text

    # soft-delete -> status='hidden' trong DB (xác nhận qua query DB trực tiếp)
    with engine.connect() as conn:
        row = conn.execute(
            text("SELECT status FROM aggregated_listings WHERE id = :id"),
            {"id": listing_id},
        ).mappings().first()
    assert row is not None
    assert row["status"] == "hidden"

    # GET /listings/{id} giờ ẩn tin hidden -> 404
    got = client.get(f"/listings/{listing_id}")
    assert got.status_code == 404, got.text

    # tin hidden không xuất hiện trong kết quả search
    search = client.get("/listings")
    assert search.status_code == 200, search.text
    ids = [item["id"] for item in search.json()["items"]]
    assert listing_id not in ids


def test_delete_other_users_listing_forbidden():
    user_a = _register()
    user_b = _register()

    created = client.post("/listings", json=_listing_payload(), headers=user_a["headers"])
    assert created.status_code == 201, created.text
    listing_id = created.json()["id"]

    r = client.delete(f"/listings/{listing_id}", headers=user_b["headers"])
    assert r.status_code == 403, r.text
