"""Narrow legacy route compatibility behavior retained during mobility rollout."""
import importlib
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient


def test_listing_route_times_accept_partial_missing_campus_values():
    from app.listings.schemas import ListingOut

    listing = ListingOut(
        id=17,
        title="Legacy fixture",
        source="test",
        route_time_campus=[1.0, None, 3.0],
    )
    assert listing.route_time_campus == [1.0, None, 3.0]


def test_legacy_route_geometry_requests_listing_to_campus(monkeypatch):
    module = importlib.import_module("app.listings.router")
    calls = []

    async def fixture_geometry(origin, destination):
        calls.append((origin, destination))
        return [[10.01, 105.77], [10.0159, 105.7656]]

    monkeypatch.setattr(module, "route_geometry", fixture_geometry)
    monkeypatch.setattr(module.settings, "ors_api_key", "fixture-only-key")
    listing = SimpleNamespace(id=17, lat=10.01, lng=105.77)

    class Repo:
        def get_visible(self, listing_id):
            return listing if listing_id == listing.id else None

    app = FastAPI()
    app.include_router(module.router)
    app.dependency_overrides[module.get_repo] = lambda: Repo()
    with TestClient(app) as client:
        response = client.get("/listings/17/route?campus=0")

    assert response.status_code == 200
    assert calls == [((10.01, 105.77), (10.0159, 105.7656))]
