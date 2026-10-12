"""Offline Routes wire contract and server-side route resolution tests."""
import asyncio
from datetime import datetime, timezone
import importlib
import json
from pathlib import Path

import httpx
import pytest

from app.mobility.campuses import get_campus
from app.mobility.contracts import (CatalogListing, Position, ResolvedRouteRequest,
                                    RouteRequest, RouteResult)
from app.mobility.providers.base import MobilitySettings


FIXTURES = Path(__file__).parent / "fixtures" / "mobility" / "routes"
API_KEY = "SENTINEL_GOOGLE_ROUTE_KEY"
POLYLINE = "_p~iF~ps|U_ulLnnqC_mqNvxq`@"
ORIGIN = {"latitude": 10.01, "longitude": 105.77}
DESTINATION = {"latitude": 10.0322, "longitude": 105.7683}
FIELD_MASK = "routes.duration,routes.distanceMeters,routes.polyline.encodedPolyline"
BUS_FIELD_MASK = (
    FIELD_MASK
    + ",routes.legs.steps.travelMode,routes.legs.steps.transitDetails.transitLine.vehicle.type"
)


def load_fixture(name):
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def route_module():
    try:
        return importlib.import_module("app.mobility.providers.google_routes")
    except ModuleNotFoundError:
        pytest.fail("Google Routes offline adapter is not implemented", pytrace=False)


def service_module():
    try:
        return importlib.import_module("app.mobility.route_service")
    except ModuleNotFoundError:
        pytest.fail("server-side route resolution service is not implemented", pytrace=False)


def resolved_request(mode, departure_time=None):
    return ResolvedRouteRequest(
        request=RouteRequest(
            listing_id=17,
            campus_id="khu_ii",
            requested_mode=mode,
            departure_time=departure_time,
        ),
        origin=Position(lat=ORIGIN["latitude"], lng=ORIGIN["longitude"], precision="APPROXIMATE"),
        destination=get_campus("khu_ii"),
    )


def configured(mode):
    return MobilitySettings(
        enabled=True,
        live_enabled=True,
        server_api_key=API_KEY,
        allowed_modes={mode},
    )


@pytest.mark.parametrize(
    "mode,google_mode",
    [
        ("MOTORBIKE", "TWO_WHEELER"),
        ("WALK", "WALK"),
        ("BICYCLE", "BICYCLE"),
        ("BUS", "TRANSIT"),
    ],
)
def test_compute_routes_uses_documented_mode_and_listing_to_campus_wire(mode, google_mode):
    module = route_module()
    captured = []
    fixture = "route_bus_success.json" if mode == "BUS" else "route_success.json"

    def respond(request):
        captured.append(request)
        return httpx.Response(200, json=load_fixture(fixture))

    transport = httpx.MockTransport(respond)
    provider = module.GoogleRoutesProvider(configured(mode), transport=transport)
    departure = datetime(2026, 10, 4, 1, 0, tzinfo=timezone.utc) if mode == "BUS" else None
    result = asyncio.run(provider.compute_route(resolved_request(mode, departure)))

    assert len(captured) == 1
    request = captured[0]
    assert str(request.url) == "https://routes.googleapis.com/directions/v2:computeRoutes"
    assert request.headers["X-Goog-Api-Key"] == API_KEY
    assert request.headers["X-Goog-FieldMask"] == (BUS_FIELD_MASK if mode == "BUS" else FIELD_MASK)
    body = json.loads(request.content)
    assert body["origin"]["location"]["latLng"] == ORIGIN
    assert body["destination"]["location"]["latLng"] == DESTINATION
    assert body["travelMode"] == google_mode
    if mode == "BUS":
        assert body["transitPreferences"] == {"allowedTravelModes": ["BUS"]}
        assert body["departureTime"] == "2026-10-04T01:00:00Z"
    else:
        assert "transitPreferences" not in body
        assert "departureTime" not in body

    assert result.status == "OK"
    assert result.requested_mode == mode and result.effective_mode == mode
    assert result.direction == "LISTING_TO_CAMPUS"
    assert result.duration_seconds == 372
    assert result.distance_meters == 4567
    assert [(point.lat, point.lng) for point in result.polyline] == [
        (38.5, -120.2), (40.7, -120.95), (43.252, -126.453),
    ]
    assert result.evidence_kind == "SYNTHETIC_FIXTURE"
    assert result.observed_at is not None and result.observed_at.utcoffset().total_seconds() == 0
    assert API_KEY not in repr(result.model_dump(mode="json"))


def test_bus_accepts_only_documented_bus_vehicle_types_with_walking_access():
    module = route_module()
    for vehicle_type in ("BUS", "INTERCITY_BUS", "TROLLEYBUS"):
        payload = load_fixture("route_bus_success.json")
        payload["routes"][0]["legs"][0]["steps"][1]["transitDetails"]["transitLine"]["vehicle"]["type"] = vehicle_type
        provider = module.GoogleRoutesProvider(
            configured("BUS"), transport=httpx.MockTransport(lambda _: httpx.Response(200, json=payload))
        )
        result = asyncio.run(provider.compute_route(
            resolved_request("BUS", datetime(2026, 10, 4, 1, 0, tzinfo=timezone.utc))
        ))
        assert result.status == "OK" and result.effective_mode == "BUS"
        assert result.duration_seconds == 372 and result.distance_meters == 4567


@pytest.mark.parametrize(
    "steps",
    [
        [{"travelMode": "WALK"}, {"travelMode": "TRANSIT", "transitDetails": {"transitLine": {"vehicle": {"type": "SUBWAY"}}}}],
        [{"travelMode": "WALK"}, {"travelMode": "TRANSIT", "transitDetails": {"transitLine": {"vehicle": {"type": "TRAIN"}}}}],
        [{"travelMode": "WALK"}, {"travelMode": "TRANSIT", "transitDetails": {"transitLine": {}}}],
        [{"travelMode": "WALK"}, {"travelMode": "TRANSIT"}],
        [{"travelMode": "WALK"}, {"travelMode": "BICYCLE"}],
        [{"travelMode": "WALK"}, {"travelMode": "TRANSIT", "transitDetails": {"transitLine": {"vehicle": {"type": "BUS"}}}}, {"travelMode": "DRIVE"}],
    ],
    ids=["subway", "rail", "missing-vehicle-type", "missing-transit-details", "walking-plus-bicycle", "drive-access"],
)
def test_bus_rejects_non_bus_or_unproven_transit_without_route_measurements(steps):
    module = route_module()
    payload = load_fixture("route_bus_success.json")
    payload["routes"][0]["legs"][0]["steps"] = steps
    provider = module.GoogleRoutesProvider(
        configured("BUS"), transport=httpx.MockTransport(lambda _: httpx.Response(200, json=payload))
    )
    result = asyncio.run(provider.compute_route(
        resolved_request("BUS", datetime(2026, 10, 4, 1, 0, tzinfo=timezone.utc))
    ))
    assert result.status == "PROVIDER_ERROR"
    assert result.effective_mode is None
    assert result.duration_seconds is None and result.distance_meters is None and result.polyline is None


def test_bus_walking_only_response_is_not_a_bus_route():
    module = route_module()
    payload = load_fixture("route_bus_success.json")
    payload["routes"][0]["legs"][0]["steps"] = [{"travelMode": "WALK"}, {"travelMode": "WALK"}]
    provider = module.GoogleRoutesProvider(
        configured("BUS"), transport=httpx.MockTransport(lambda _: httpx.Response(200, json=payload))
    )
    result = asyncio.run(provider.compute_route(
        resolved_request("BUS", datetime(2026, 10, 4, 1, 0, tzinfo=timezone.utc))
    ))
    assert result.status == "PROVIDER_ERROR"
    assert result.duration_seconds is None and result.distance_meters is None and result.polyline is None


def test_empty_routes_array_is_no_route_but_missing_routes_is_malformed():
    module = route_module()

    async def compute(payload):
        provider = module.GoogleRoutesProvider(
            configured("WALK"), transport=httpx.MockTransport(lambda _: httpx.Response(200, json=payload))
        )
        return await provider.compute_route(resolved_request("WALK"))

    no_route = asyncio.run(compute(load_fixture("route_no_route.json")))
    malformed = asyncio.run(compute(load_fixture("route_malformed.json")))
    assert no_route.status == "NO_ROUTE"
    assert no_route.duration_seconds is None and no_route.distance_meters is None and no_route.polyline is None
    assert malformed.status == "PROVIDER_ERROR"
    assert malformed.duration_seconds is None and malformed.distance_meters is None and malformed.polyline is None


@pytest.mark.parametrize(
    "mutate",
    [
        lambda route: route.update(duration="not-seconds"),
        lambda route: route.update(duration="-1s"),
        lambda route: route.update(distanceMeters=-1),
        lambda route: route.update(distanceMeters="4567"),
        lambda route: route.update(polyline={"encodedPolyline": "_"}),
        lambda route: route.update(polyline={"encodedPolyline": "\u0001"}),
    ],
    ids=["bad-duration", "negative-duration", "negative-distance", "string-distance", "truncated-polyline", "invalid-polyline-char"],
)
def test_invalid_route_measurement_or_polyline_is_provider_error(mutate):
    module = route_module()
    payload = load_fixture("route_success.json")
    mutate(payload["routes"][0])
    provider = module.GoogleRoutesProvider(
        configured("WALK"), transport=httpx.MockTransport(lambda _: httpx.Response(200, json=payload))
    )
    result = asyncio.run(provider.compute_route(resolved_request("WALK")))
    assert result.status == "PROVIDER_ERROR"
    assert result.duration_seconds is None and result.distance_meters is None and result.polyline is None


@pytest.mark.parametrize(
    "status,expected",
    [(429, "RATE_LIMITED"), (403, "PROVIDER_ERROR"), (503, "PROVIDER_ERROR")],
)
def test_http_errors_have_structured_status_and_no_measurement(status, expected):
    module = route_module()
    provider = module.GoogleRoutesProvider(
        configured("WALK"), transport=httpx.MockTransport(lambda _: httpx.Response(status, text=API_KEY))
    )
    result = asyncio.run(provider.compute_route(resolved_request("WALK")))
    assert result.status == expected
    assert result.duration_seconds is None and result.distance_meters is None and result.polyline is None
    assert API_KEY not in repr(result.model_dump(mode="json"))


def test_timeout_does_not_leak_provider_exception_or_key(caplog):
    module = route_module()

    def timeout(_):
        raise httpx.ReadTimeout(f"request failed with {API_KEY}")

    provider = module.GoogleRoutesProvider(configured("WALK"), transport=httpx.MockTransport(timeout))
    result = asyncio.run(provider.compute_route(resolved_request("WALK")))
    assert result.status == "PROVIDER_ERROR"
    assert result.duration_seconds is None and result.distance_meters is None and result.polyline is None
    assert API_KEY not in repr(result.model_dump(mode="json"))
    assert API_KEY not in caplog.text


def test_timeout_bounds_the_whole_mock_transport_request():
    module = route_module()

    async def slow_response(_):
        await asyncio.sleep(0.05)
        return httpx.Response(200, json=load_fixture("route_success.json"))

    config = configured("WALK").model_copy(update={"timeout_seconds": 0.001})
    provider = module.GoogleRoutesProvider(config, transport=httpx.MockTransport(slow_response))
    result = asyncio.run(provider.compute_route(resolved_request("WALK")))
    assert result.status == "PROVIDER_ERROR"
    assert result.duration_seconds is None and result.distance_meters is None and result.polyline is None


@pytest.mark.parametrize(
    "config,transport,status",
    [
        (MobilitySettings(), httpx.MockTransport(lambda _: httpx.Response(500)), "NOT_CONFIGURED"),
        (MobilitySettings(enabled=True, live_enabled=True, server_api_key=API_KEY),
         httpx.MockTransport(lambda _: httpx.Response(500)), "CAPABILITY_UNVERIFIED"),
        (MobilitySettings(enabled=True, live_enabled=True, server_api_key=API_KEY, allowed_modes={"WALK"}),
         None, "CAPABILITY_UNVERIFIED"),
    ],
)
def test_disabled_or_unverified_statuses_do_not_construct_http_client(monkeypatch, config, transport, status):
    module = route_module()

    def forbidden_client(*args, **kwargs):
        raise AssertionError("HTTP client must not be created before the request gate permits a fixture")

    monkeypatch.setattr(module.httpx, "AsyncClient", forbidden_client)
    provider = module.GoogleRoutesProvider(config, transport=transport)
    result = asyncio.run(provider.compute_route(resolved_request("WALK")))
    assert result.status == status
    assert result.observed_at is None and result.evidence_kind == "NONE"
    assert result.duration_seconds is None and result.distance_meters is None and result.polyline is None


def test_non_mock_transport_is_blocked_without_sending_request(monkeypatch):
    module = route_module()

    class CountingTransport(httpx.AsyncBaseTransport):
        def __init__(self):
            self.calls = 0

        async def handle_async_request(self, request):
            self.calls += 1
            raise AssertionError("non-fixture transport must never run")

        async def aclose(self):
            return None

    transport = CountingTransport()
    config = configured("WALK")
    provider = module.GoogleRoutesProvider(config, transport=transport)
    result = asyncio.run(provider.compute_route(resolved_request("WALK")))
    assert result.status == "CAPABILITY_UNVERIFIED"
    assert transport.calls == 0


def test_route_service_resolves_listing_to_campus_and_maps_unknown_id():
    module = service_module()
    listing = CatalogListing(
        id=17,
        title="Synthetic listing",
        source="test",
        source_id="fixture-17",
        position=Position(lat=ORIGIN["latitude"], lng=ORIGIN["longitude"], precision="APPROXIMATE"),
    )

    class Catalog:
        def get_listing(self, listing_id):
            return listing if listing_id == listing.id else None

    class Provider:
        def __init__(self):
            self.received = []

        async def compute_route(self, request):
            self.received.append(request)
            return RouteResult(
                listing_id=request.request.listing_id,
                campus_id=request.request.campus_id,
                requested_mode=request.request.requested_mode,
                effective_mode=request.request.requested_mode,
                status="OK",
                duration_seconds=372,
                distance_meters=4567,
                coordinate_version=request.destination.coordinate_version,
                evidence_kind="SYNTHETIC_FIXTURE",
                observed_at=datetime(2026, 10, 4, 1, 0, tzinfo=timezone.utc),
            )

    provider = Provider()
    service = module.RouteService(Catalog(), provider)
    request = RouteRequest(listing_id=17, campus_id="khu_ii", requested_mode="WALK")
    result = asyncio.run(service.route(request))
    assert len(provider.received) == 1
    resolved = provider.received[0]
    assert (resolved.origin.lat, resolved.origin.lng) == (10.01, 105.77)
    assert (resolved.destination.lat, resolved.destination.lng) == (10.0322, 105.7683)
    assert resolved.request.direction == "LISTING_TO_CAMPUS"
    assert result.status == "OK" and result.coordinate_version == "legacy-2026-07-06-provisional"
    with pytest.raises(LookupError):
        asyncio.run(service.route(request.model_copy(update={"listing_id": 999})))
    assert len(provider.received) == 1


def test_route_service_missing_position_returns_without_provider_call():
    module = service_module()
    listing = CatalogListing(id=18, title="No position", source="test", source_id="fixture-18")

    class Catalog:
        def get_listing(self, listing_id):
            return listing if listing_id == listing.id else None

    class Provider:
        def __init__(self):
            self.calls = 0

        async def compute_route(self, request):
            self.calls += 1
            raise AssertionError("provider must not run when listing position is missing")

    provider = Provider()
    result = asyncio.run(module.RouteService(Catalog(), provider).route(
        RouteRequest(listing_id=18, campus_id="khu_i", requested_mode="WALK")
    ))
    assert result.status == "LOCATION_UNAVAILABLE"
    assert result.duration_seconds is None and result.distance_meters is None and result.polyline is None
    assert result.observed_at is None and result.evidence_kind == "NONE"
    assert provider.calls == 0
