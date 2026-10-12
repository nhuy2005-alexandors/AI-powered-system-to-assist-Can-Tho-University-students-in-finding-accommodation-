"""Offline Places adapter and service contracts; no Google calls are made."""
import asyncio
import importlib
import json
from pathlib import Path

import httpx
import pytest

from app.mobility.contracts import (
    CatalogListing,
    NearbyRequest,
    Position,
    ResolvedNearbyRequest,
)
from app.mobility.providers.base import MobilitySettings


FIXTURES = Path(__file__).parent / "fixtures/mobility/places"
FIELD_MASK = "places.id,places.displayName,places.location,places.types,places.attributions"
CATEGORY_TYPES = {
    "grocery": ["grocery_store", "supermarket"],
    "market": ["market"],
    "pharmacy": ["pharmacy"],
    "healthcare": ["hospital", "medical_clinic"],
    "police": ["police"],
    "bus_stop": ["bus_stop"],
}


def places_module():
    try:
        return importlib.import_module("app.mobility.providers.google_places")
    except ModuleNotFoundError as exc:
        pytest.fail(f"Google Places adapter is not implemented: {exc.name}")


def service_module():
    try:
        return importlib.import_module("app.mobility.place_service")
    except ModuleNotFoundError as exc:
        pytest.fail(f"Places service is not implemented: {exc.name}")


def resolved(*, radius=500, categories=("grocery",), center=(10.0, 105.0)):
    request = NearbyRequest(listing_id=7, radius_m=radius, categories=list(categories))
    position = Position(lat=center[0], lng=center[1], precision="APPROXIMATE", source="fixture")
    return ResolvedNearbyRequest(request=request, center=position)


def fixture(name):
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def run(coroutine):
    return asyncio.run(coroutine)


def configured(categories, *, timeout_seconds=10.0):
    return MobilitySettings(
        enabled=True,
        live_enabled=True,
        server_api_key="test-only-synthetic-key",
        timeout_seconds=timeout_seconds,
        allowed_categories=set(categories),
    )


def test_disabled_and_unverified_requests_do_not_construct_http_client(monkeypatch):
    module = places_module()
    constructions = []

    def forbidden_client(*args, **kwargs):
        constructions.append((args, kwargs))
        raise AssertionError("HTTP client must not be created before the mobility gate passes")

    monkeypatch.setattr(module.httpx, "AsyncClient", forbidden_client)
    request = resolved()
    transport = httpx.MockTransport(lambda _: httpx.Response(200, json={"places": []}))

    disabled = module.GooglePlacesProvider(MobilitySettings(), transport=transport)
    unverified = module.GooglePlacesProvider(configured([]), transport=transport)
    disabled_result, unverified_result = run(disabled.nearby(request)), run(unverified.nearby(request))

    assert disabled_result.status == "NOT_CONFIGURED"
    assert disabled_result.evidence_kind == "NONE" and disabled_result.queried_at is None
    assert unverified_result.status == "CAPABILITY_UNVERIFIED"
    assert unverified_result.evidence_kind == "NONE" and unverified_result.queried_at is None
    assert constructions == []


@pytest.mark.parametrize("radius", [500, 1000, 2000])
def test_request_uses_documented_circle_limit_and_selected_field_mask(radius):
    module = places_module()
    requests = []
    transport = httpx.MockTransport(
        lambda request: requests.append(request) or httpx.Response(200, json=fixture("empty.json"))
    )
    provider = module.GooglePlacesProvider(configured(["grocery"]), transport=transport)

    result = run(provider.nearby(resolved(radius=radius)))

    assert result.status == "EMPTY"
    assert len(requests) == 1
    request = requests[0]
    assert request.method == "POST"
    assert str(request.url) == "https://places.googleapis.com/v1/places:searchNearby"
    assert request.headers["X-Goog-FieldMask"] == FIELD_MASK
    assert json.loads(request.content) == {
        "includedTypes": ["grocery_store", "supermarket"],
        "maxResultCount": 20,
        "locationRestriction": {
            "circle": {
                "center": {"latitude": 10.0, "longitude": 105.0},
                "radius": radius,
            }
        },
    }


@pytest.mark.parametrize("category,expected_types", list(CATEGORY_TYPES.items()))
def test_every_requested_category_uses_the_official_type_mapping(category, expected_types):
    module = places_module()
    requests = []
    transport = httpx.MockTransport(
        lambda request: requests.append(request) or httpx.Response(200, json=fixture("empty.json"))
    )
    provider = module.GooglePlacesProvider(configured([category]), transport=transport)

    result = run(provider.nearby(resolved(categories=(category,))))

    assert json.loads(requests[0].content)["includedTypes"] == expected_types
    assert result.categories == [category]


def test_one_unverified_requested_category_blocks_the_whole_request_without_http(monkeypatch):
    module = places_module()
    calls = []

    def forbidden_client(*args, **kwargs):
        calls.append((args, kwargs))
        raise AssertionError("partial category queries would silently omit requested categories")

    monkeypatch.setattr(module.httpx, "AsyncClient", forbidden_client)
    provider = module.GooglePlacesProvider(configured(["grocery"]), transport=httpx.MockTransport(
        lambda _: httpx.Response(200, json={"places": []})
    ))

    result = run(provider.nearby(resolved(categories=("grocery", "police"))))

    assert result.status == "CAPABILITY_UNVERIFIED"
    assert result.categories == ["grocery", "police"]
    assert result.coverage == "UNKNOWN" and result.items == [] and not result.truncated
    assert result.evidence_kind == "NONE" and result.queried_at is None
    assert calls == []


def test_valid_empty_is_observed_but_malformed_and_provider_errors_remain_unknown():
    module = places_module()

    def call(status, payload=None, content=None):
        def respond(_):
            if content is not None:
                return httpx.Response(status, content=content)
            return httpx.Response(status, json=payload)

        provider = module.GooglePlacesProvider(
            configured(["grocery"]), transport=httpx.MockTransport(respond)
        )
        return run(provider.nearby(resolved()))

    empty = call(200, fixture("empty.json"))
    malformed = call(200, {})
    invalid_json = call(200, content=b"not-json")
    rate_limited = call(429, {"error": {"message": "synthetic"}})
    provider_error = call(503, {"error": {"message": "synthetic"}})

    assert empty.status == "EMPTY" and empty.coverage == "PARTIAL"
    assert empty.evidence_kind == "SYNTHETIC_FIXTURE" and empty.queried_at is not None
    assert empty.queried_at.utcoffset().total_seconds() == 0
    for result, status in (
        (malformed, "PROVIDER_ERROR"),
        (invalid_json, "PROVIDER_ERROR"),
        (rate_limited, "RATE_LIMITED"),
        (provider_error, "PROVIDER_ERROR"),
    ):
        assert result.status == status
        assert result.items == [] and result.coverage == "UNKNOWN" and not result.truncated
        assert result.evidence_kind == "SYNTHETIC_FIXTURE" and result.queried_at is not None


def test_provider_error_does_not_expose_transport_or_provider_details():
    module = places_module()

    def fail(_):
        raise httpx.ConnectError("sentinel-private-host-key")

    provider = module.GooglePlacesProvider(
        configured(["grocery"]), transport=httpx.MockTransport(fail)
    )
    result = run(provider.nearby(resolved()))

    assert result.status == "PROVIDER_ERROR"
    assert "sentinel-private-host-key" not in result.model_dump_json()
    assert result.coverage == "UNKNOWN" and result.items == [] and not result.truncated


@pytest.mark.parametrize("axis,wire_value", [
    ("latitude", "91"),
    ("longitude", "181"),
    ("latitude", "NaN"),
    ("longitude", "Infinity"),
])
def test_invalid_provider_coordinates_are_errors_before_radius_filtering(axis, wire_value):
    module = places_module()
    payload = fixture("nearby_success.json")
    payload["places"] = payload["places"][:1]
    original_value = payload["places"][0]["location"][axis]
    body = json.dumps(payload).replace(
        f'"{axis}": {original_value}', f'"{axis}": {wire_value}', 1
    ).encode("utf-8")
    provider = module.GooglePlacesProvider(
        configured(["grocery"]),
        transport=httpx.MockTransport(lambda _: httpx.Response(
            200, content=body, headers={"Content-Type": "application/json"}
        )),
    )

    result = run(provider.nearby(resolved()))

    assert result.status == "PROVIDER_ERROR"
    assert result.items == [] and result.coverage == "UNKNOWN" and not result.truncated
    assert result.evidence_kind == "SYNTHETIC_FIXTURE" and result.queried_at is not None


def test_slow_async_transport_is_bounded_by_configured_timeout():
    module = places_module()

    class SlowMockTransport(httpx.MockTransport):
        async def handle_async_request(self, request):
            await asyncio.sleep(0.08)
            return httpx.Response(200, json=fixture("empty.json"), request=request)

    provider = module.GooglePlacesProvider(
        configured(["grocery"], timeout_seconds=0.01),
        transport=SlowMockTransport(lambda _: httpx.Response(200, json=fixture("empty.json"))),
    )

    result = run(provider.nearby(resolved()))

    assert result.status == "PROVIDER_ERROR"
    assert result.items == [] and result.coverage == "UNKNOWN" and not result.truncated
    assert result.evidence_kind == "SYNTHETIC_FIXTURE" and result.queried_at is not None


def test_success_selects_only_safe_place_fields_and_filters_outside_radius():
    module = places_module()
    transport = httpx.MockTransport(
        lambda _: httpx.Response(200, json=fixture("nearby_success.json"))
    )
    provider = module.GooglePlacesProvider(configured(["grocery", "healthcare"]), transport=transport)

    result = run(provider.nearby(resolved(categories=("grocery", "healthcare"))))

    assert result.status == "OK" and result.coverage == "PARTIAL"
    assert result.categories == ["grocery", "healthcare"]
    assert result.center_precision == "APPROXIMATE"
    assert len(result.items) == 1
    place = result.items[0]
    assert place.model_dump() == {
        "provider_place_id": "place-near-1",
        "name": "Synthetic Grocery",
        "category": "grocery",
        "lat": 10.001,
        "lng": 105.0,
        "straight_line_distance_m": pytest.approx(111.195, abs=0.02),
        "attribution": ["Synthetic Maps Contributor (https://maps.example.test/contributor)"],
    }
    assert set(place.model_dump()) == {
        "provider_place_id", "name", "category", "lat", "lng",
        "straight_line_distance_m", "attribution",
    }
    assert "nationalPhoneNumber" not in result.model_dump_json()
    assert "reviews" not in result.model_dump_json()


def test_success_at_twenty_results_is_saturated_and_never_paginates():
    module = places_module()
    places = [
        {
            "id": f"place-{index}",
            "displayName": {"text": f"Synthetic Grocery {index}"},
            "location": {"latitude": 10.0001, "longitude": 105.0},
            "types": ["grocery_store"],
            "attributions": [],
        }
        for index in range(21)
    ]
    requests = []
    transport = httpx.MockTransport(
        lambda request: requests.append(request) or httpx.Response(200, json={"places": places})
    )
    provider = module.GooglePlacesProvider(configured(["grocery"]), transport=transport)

    result = run(provider.nearby(resolved()))

    assert len(result.items) == 20
    assert result.truncated is True
    assert result.coverage == "PARTIAL"
    assert "pageToken" not in json.loads(requests[0].content)
    assert "pageToken" not in str(requests[0].url)


def test_place_service_unknown_id_raises_and_missing_position_never_calls_provider():
    module = places_module()
    services = service_module()

    class Catalog:
        def get_listing(self, listing_id):
            if listing_id == 8:
                return CatalogListing(id=8, title="No location", source="fixture", source_id="8")
            return None

    class Provider:
        def __init__(self):
            self.calls = []

        async def nearby(self, request):
            self.calls.append(request)
            return await module.GooglePlacesProvider(MobilitySettings()).nearby(request)

    provider = Provider()
    service = services.PlaceService(Catalog(), provider)

    with pytest.raises(LookupError):
        run(service.nearby(NearbyRequest(listing_id=99, categories=["police"])))
    result = run(service.nearby(NearbyRequest(listing_id=8, radius_m=2000, categories=["police"])))

    assert provider.calls == []
    assert result.status == "LOCATION_UNAVAILABLE"
    assert result.listing_id == 8 and result.radius_m == 2000 and result.categories == ["police"]
    assert result.evidence_kind == "NONE" and result.queried_at is None
    assert result.coverage == "UNKNOWN" and result.items == [] and not result.truncated
