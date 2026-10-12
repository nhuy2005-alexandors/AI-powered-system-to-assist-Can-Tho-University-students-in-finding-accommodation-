"""In-process API boundary: real services, no database or network."""
from importlib import import_module

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

from app.mobility.contracts import CatalogListing, CatalogPage, Position


class MemoryCatalog:
    def get_listing(self, listing_id):
        if listing_id == 1:
            return CatalogListing(id=1, title="Synthetic studio", source="chotot", source_id="test-1",
                                  housing_type="studio", description_is_partial=True,
                                  position=Position(lat=10.01, lng=105.77, precision="APPROXIMATE"))
        if listing_id == 2:
            return CatalogListing(id=2, title="Synthetic no location", source="chotot", source_id="test-2")
        return None

    def list_page(self, page=1, size=50, bbox=None):
        rows = [self.get_listing(1), self.get_listing(2)]
        return CatalogPage(items=rows[(page-1)*size:page*size], total=2, page=page, size=size)


def client(catalog=None, *, enabled=True, open_settings=None, demo_geocode_enabled=False):
    try:
        module = import_module("app.mobility.router")
    except ModuleNotFoundError:
        pytest.fail("mobility API router is not implemented")
    app = FastAPI()
    module.install_mobility(app, catalog=catalog, enabled=enabled, open_settings=open_settings,
                            demo_geocode_enabled=demo_geocode_enabled)
    return TestClient(app)


def test_disabled_feature_has_no_registered_mobility_routes():
    assert client(enabled=False).get("/mobility/campuses").status_code == 404


def test_explicit_geocode_endpoint_is_disabled_by_default_and_validates_input():
    c = client(MemoryCatalog(), demo_geocode_enabled=True)
    body = {"address":"Synthetic public place", "bounds":{"south":9.9,"north":10.2,"west":105.5,"east":105.9}}
    assert client(MemoryCatalog()).post("/mobility/geocode", json=body).status_code == 404
    response = c.post("/mobility/geocode", json=body)
    assert response.status_code == 200
    assert response.json()["status"] == "NOT_CONFIGURED"
    assert response.json()["position"] is None
    assert c.post("/mobility/geocode", json=body | {"url":"https://unapproved.test"}).status_code == 422
    assert client(enabled=False).post("/mobility/geocode", json=body).status_code == 404
    for private_text in ("Call 0901234567", "Contact demo@example.test"):
        assert c.post("/mobility/geocode", json=body | {"address":private_text}).status_code == 422


def test_legacy_google_flags_and_key_do_not_select_google_route_or_places(monkeypatch):
    from app.mobility.providers.base import MobilitySettings

    router = import_module("app.mobility.router")
    google_routes = import_module("app.mobility.providers.google_routes")
    google_places = import_module("app.mobility.providers.google_places")
    constructors = []
    route_constructor = google_routes.GoogleRoutesProvider
    places_constructor = google_places.GooglePlacesProvider

    def record_route_constructor(*args, **kwargs):
        constructors.append("routes")
        return route_constructor(*args, **kwargs)

    def record_places_constructor(*args, **kwargs):
        constructors.append("places")
        return places_constructor(*args, **kwargs)

    monkeypatch.setattr(google_routes, "GoogleRoutesProvider", record_route_constructor)
    monkeypatch.setattr(google_places, "GooglePlacesProvider", record_places_constructor)

    app = FastAPI()
    router.install_mobility(
        app,
        catalog=MemoryCatalog(),
        enabled=True,
        config=MobilitySettings(
            enabled=True,
            live_enabled=True,
            server_api_key="sentinel-legacy-google-key",
        ),
    )
    c = TestClient(app)

    route_response = c.post("/mobility/routes", json={
        "listing_id": 1, "campus_id": "khu_ii", "requested_mode": "WALK",
    })
    nearby_response = c.post("/mobility/nearby", json={
        "listing_id": 1, "radius_m": 500, "categories": ["police"],
    })

    assert route_response.status_code == 200
    assert (route_response.json()["provider"], route_response.json()["status"]) == (
        "none", "NOT_CONFIGURED",
    )
    assert nearby_response.status_code == 200
    assert (nearby_response.json()["provider"], nearby_response.json()["status"]) == (
        "none", "NOT_CONFIGURED",
    )
    assert constructors == []


def test_campuses_and_paginated_catalog_keep_missing_location():
    c = client(MemoryCatalog())
    assert [r["id"] for r in c.get("/mobility/campuses").json()] == ["khu_i", "khu_ii", "khu_iii"]
    response = c.get("/mobility/listings?page=2&size=1")
    assert response.status_code == 200
    assert response.json()["items"][0]["id"] == 2
    assert response.json()["items"][0]["position"] is None
    assert response.json()["total"] == 2


def test_missing_catalog_configuration_is_503_not_empty_success():
    response = client().get("/mobility/listings")
    assert response.status_code == 503
    assert response.json()["detail"] == "DATASET_NOT_READY"


def test_catalog_failure_does_not_disclose_error_or_dsn():
    c = client(MemoryCatalog())
    def unavailable(**kwargs):
        from app.mobility.catalog_repo import CatalogUnavailable
        raise CatalogUnavailable("postgresql://user:sentinel-password@private.test/db")
    c.app.state.mobility_catalog.list_page = unavailable
    response = c.get("/mobility/listings")
    assert response.status_code == 503
    assert "sentinel-password" not in response.text


@pytest.mark.parametrize("body", [
    {"listing_id": 1, "campus_id": "khu_ii", "requested_mode": "DRIVE"},
    {"listing_id": 1, "campus_id": "khu_ii", "requested_mode": "BUS"},
    {"listing_id": 1, "campus_id": "khu_ii", "requested_mode": "WALK", "url": "https://bad.test"},
])
def test_route_validation_happens_before_provider(body):
    assert client(MemoryCatalog()).post("/mobility/routes", json=body).status_code == 422


def test_default_routes_are_keyless_with_separate_campus_results():
    c = client(MemoryCatalog())
    statuses = []
    for campus in ("khu_i", "khu_ii", "khu_iii"):
        response = c.post("/mobility/routes", json={
            "listing_id": 1, "campus_id": campus, "requested_mode": "WALK",
        })
        assert response.status_code == 200
        result = response.json()
        assert result["campus_id"] == campus
        assert result["duration_seconds"] is None and result["distance_meters"] is None
        assert result["evidence_kind"] == "NONE"
        statuses.append(result["status"])
    assert statuses == ["NOT_CONFIGURED"] * 3


@pytest.mark.parametrize(
    ("requested_mode", "expected_status"),
    [
        ("MOTORBIKE", "UNSUPPORTED_MODE"),
        ("BUS", "UNSUPPORTED_MODE"),
        ("WALK", "NOT_CONFIGURED"),
        ("BICYCLE", "NOT_CONFIGURED"),
    ],
)
def test_selected_ors_preserves_mode_precedence_without_endpoint_or_live_config(
    monkeypatch, requested_mode, expected_status,
):
    """Mode capability is resolved before provider configuration, with no I/O."""
    from app.mobility.providers.open_config import OpenMobilitySettings
    from app.mobility.providers import network_policy

    def fail_resolver(_host):
        raise AssertionError("unconfigured route must not resolve provider DNS")

    monkeypatch.setattr(network_policy, "_resolve_addresses", fail_resolver)
    settings = OpenMobilitySettings(
        _env_file=None,
        enabled=True,
        live_enabled=False,
        routing_provider="ors",
        ors_base_url="",
    )
    body = {
        "listing_id": 1,
        "campus_id": "khu_ii",
        "requested_mode": requested_mode,
    }
    if requested_mode == "BUS":
        body["departure_time"] = "2026-10-07T12:00:00+07:00"

    response = client(MemoryCatalog(), open_settings=settings).post(
        "/mobility/routes", json=body,
    )

    assert response.status_code == 200
    result = response.json()
    assert result["provider"] == "ors"
    assert result["status"] == expected_status
    assert result["duration_seconds"] is None
    assert result["distance_meters"] is None
    assert result["evidence_kind"] == "NONE"
    assert result["effective_mode"] is None


@pytest.mark.parametrize("mode", ["MOTORBIKE", "BUS", "WALK", "BICYCLE"])
def test_selected_ors_missing_key_and_policy_resolves_capability_before_configuration(monkeypatch, mode):
    from app.mobility.providers.open_config import OpenMobilitySettings
    import httpx
    import socket

    def no_io(*args, **kwargs):
        pytest.fail("unconfigured route attempted external I/O")

    monkeypatch.setattr(socket, "getaddrinfo", no_io)
    monkeypatch.setattr(httpx.AsyncClient, "send", no_io)
    settings = OpenMobilitySettings(
        _env_file=None, enabled=True, live_enabled=True, routing_provider="ors",
        ors_base_url="https://unit.example.test", ors_api_key="",
        provider_policies={}, expected_policy_hashes={},
    )
    body = {"listing_id": 1, "campus_id": "khu_ii", "requested_mode": mode}
    if mode == "BUS":
        body["departure_time"] = "2026-10-07T12:00:00+07:00"
    result = client(MemoryCatalog(), open_settings=settings).post("/mobility/routes", json=body).json()
    assert result["status"] == ("UNSUPPORTED_MODE" if mode in ("MOTORBIKE", "BUS") else "NOT_CONFIGURED")
    assert result["effective_mode"] is None
    assert result["duration_seconds"] is result["distance_meters"] is result["polyline"] is None
    assert result["evidence_kind"] == "NONE"


def test_selected_ors_preserves_request_catalog_and_location_validation():
    from app.mobility.providers.open_config import OpenMobilitySettings
    from app.mobility.catalog_repo import CatalogUnavailable

    settings = OpenMobilitySettings(_env_file=None, enabled=True, routing_provider="ors")
    body = {"listing_id": 1, "campus_id": "khu_ii", "requested_mode": "MOTORBIKE"}
    c = client(MemoryCatalog(), open_settings=settings)
    assert c.post("/mobility/routes", json=body | {"requested_mode": "BUS"}).status_code == 422
    assert c.post("/mobility/routes", json=body | {"listing_id": 99}).status_code == 404
    assert c.post("/mobility/routes", json=body | {"listing_id": 2}).json()["status"] == "LOCATION_UNAVAILABLE"
    assert client(open_settings=settings).post("/mobility/routes", json=body).status_code == 503
    def unavailable(_listing_id):
        raise CatalogUnavailable("unit catalog unavailable")
    c.app.state.mobility_catalog.get_listing = unavailable
    assert c.post("/mobility/routes", json=body).status_code == 503


def test_missing_location_and_missing_listing_are_distinct():
    c = client(MemoryCatalog())
    body = {"listing_id": 2, "campus_id": "khu_i", "requested_mode": "WALK"}
    result = c.post("/mobility/routes", json=body)
    assert result.status_code == 200 and result.json()["status"] == "LOCATION_UNAVAILABLE"
    assert c.post("/mobility/routes", json=body | {"listing_id": 99}).status_code == 404


def test_nearby_error_status_does_not_claim_empty_observation():
    response = client(MemoryCatalog()).post("/mobility/nearby", json={
        "listing_id": 1, "radius_m": 500, "categories": ["police"],
    })
    assert response.status_code == 200
    result = response.json()
    assert result["status"] == "NOT_CONFIGURED"
    assert result["coverage"] == "UNKNOWN"
    assert result["radius_m"] == 500 and result["categories"] == ["police"]


def test_bbox_requires_complete_ordered_coordinate_set():
    c = client(MemoryCatalog())
    assert c.get("/mobility/listings?south=10").status_code == 422
    assert c.get("/mobility/listings?south=11&north=10&west=105&east=106").status_code == 422
    assert c.get("/mobility/listings?south=10&north=11&west=105&east=106").status_code == 200


def test_main_enabled_without_catalog_dsn_registers_safe_routes(monkeypatch):
    from app.config import settings
    from pydantic import SecretStr
    import importlib
    monkeypatch.setattr(settings, "mobility_enabled", True)
    monkeypatch.setattr(settings, "mobility_database_url", SecretStr(""))
    module = importlib.import_module("app.main")
    module = importlib.reload(module)
    try:
        c = TestClient(module.app)
        assert c.get("/mobility/campuses").status_code == 200
        assert c.get("/mobility/listings").status_code == 503
    finally:
        module.engine.dispose()
        module.redis_client.close()
        monkeypatch.setattr(settings, "mobility_enabled", False)
        importlib.reload(module)
