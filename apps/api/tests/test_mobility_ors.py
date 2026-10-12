"""Offline ORS routing contract tests using synthetic MockTransport responses."""
import asyncio
from datetime import datetime, timedelta, timezone
import importlib
import json
from pathlib import Path

import httpx
import pytest

from app.mobility.contracts import Campus, Position, ResolvedRouteRequest, RouteRequest


FIXTURES = Path(__file__).parent / "fixtures/open_mobility/ors"
ORS_SECRET = "synthetic-ors-secret"
BASE_URL = "https://ors.example.test"
WALK_PATH = "/openrouteservice/v2/directions/foot-walking/geojson"
BIKE_PATH = "/openrouteservice/v2/directions/cycling-regular/geojson"
ATTRIBUTION = "Synthetic ORS attribution"


def ors_provider_type():
    try:
        module = importlib.import_module("app.mobility.providers.ors_routes")
    except ModuleNotFoundError:
        module = None
    assert module is not None, "expected the owned ORS adapter module to exist"
    provider_type = getattr(module, "ORSRouteProvider", None)
    assert provider_type is not None, "expected ORSRouteProvider in the owned adapter module"
    return provider_type


def route_request(mode, *, departure_time=None):
    return ResolvedRouteRequest(
        request=RouteRequest(
            listing_id=17,
            campus_id="khu_ii",
            requested_mode=mode,
            departure_time=departure_time,
        ),
        origin=Position(lat=10.01, lng=105.77, precision="APPROXIMATE", source="synthetic-listing"),
        destination=Campus(
            id="khu_ii",
            name="Synthetic campus",
            lat=10.03,
            lng=105.76,
            coordinate_version="synthetic-campus-v1",
            verification_status="PROVISIONAL",
        ),
    )


def route_fixture():
    return json.loads((FIXTURES / "route_success.json").read_text(encoding="utf-8"))


class FakeClock:
    def __init__(self):
        self.now = datetime(2026, 10, 5, 12, tzinfo=timezone.utc)
        self.elapsed = 0.0

    def monotonic(self):
        return self.elapsed

    def utcnow(self):
        return self.now

    async def sleep(self, seconds):
        self.elapsed += seconds
        self.now += timedelta(seconds=seconds)
        await asyncio.sleep(0)


async def public_resolver(_host):
    return ("93.184.216.34",)


def open_settings(
    *,
    max_requests=4,
    api_key=ORS_SECRET,
    allowed_paths=(WALK_PATH, BIKE_PATH),
    allowed_capabilities=("route:WALK", "route:BICYCLE"),
    include_policy=True,
    enabled=True,
    live_enabled=True,
    routing_provider="ors",
    ors_base_url=BASE_URL,
):
    network = importlib.import_module("app.mobility.providers.network_policy")
    config = importlib.import_module("app.mobility.providers.open_config")
    policy = network.ProviderPolicy(
        provider="ors",
        base_url=BASE_URL,
        allowed_paths=allowed_paths,
        allowed_capabilities=allowed_capabilities,
        attribution=(ATTRIBUTION,),
        user_agent="NCKH synthetic ORS adapter tests",
        policy_sha256="0" * 64,
        approved_until=datetime(2026, 10, 6, tzinfo=timezone.utc),
        max_requests=max_requests,
        max_rps=1.0,
        max_concurrency=1,
        timeout_seconds=10.0,
        connect_timeout_seconds=2.0,
        max_response_bytes=1_048_576,
    )
    digest = network.policy_digest(policy)
    policy = policy.model_copy(update={"policy_sha256": digest})
    return config.OpenMobilitySettings(
        _env_file=None,
        enabled=enabled,
        live_enabled=live_enabled,
        routing_provider=routing_provider,
        ors_api_key=api_key,
        ors_base_url=ors_base_url,
        provider_policies={"ors": policy} if include_policy else {},
        expected_policy_hashes={"ors": digest} if include_policy else {},
    )


def make_provider(provider_type, settings, transport, clock=None):
    clock = clock or FakeClock()
    settings.get_request_policy_gate(
        transport=transport,
        resolver=public_resolver,
        clock=clock,
    )
    return provider_type(settings, transport=transport)


@pytest.mark.parametrize(
    "mode,path,profile",
    [
        ("WALK", WALK_PATH, "foot-walking"),
        ("BICYCLE", BIKE_PATH, "cycling-regular"),
    ],
)
def test_supported_mode_uses_exact_ors_profile_and_listing_to_campus_coordinates(mode, path, profile):
    provider_type = ors_provider_type()
    requests = []
    transport = httpx.MockTransport(
        lambda request: requests.append(request) or httpx.Response(200, json=route_fixture())
    )
    provider = make_provider(provider_type, open_settings(), transport)

    result = asyncio.run(provider.compute_route(route_request(mode)))

    assert len(requests) == 1
    sent = requests[0]
    assert sent.method == "POST"
    assert sent.url == f"{BASE_URL}{path}"
    assert json.loads(sent.content) == {"coordinates": [[105.77, 10.01], [105.76, 10.03]]}
    assert sent.headers["Authorization"] == ORS_SECRET
    assert ORS_SECRET not in str(sent.url)
    assert ORS_SECRET.encode("utf-8") not in sent.content
    assert result.provider == "ors"
    assert result.provider_profile == profile
    assert result.attribution == [ATTRIBUTION]
    assert result.requested_mode == mode and result.effective_mode == mode
    assert result.status == "OK"
    assert result.duration_seconds == 372.5
    assert result.distance_meters == 4567.25
    assert [(point.lat, point.lng) for point in result.polyline] == [(10.01, 105.77), (10.03, 105.76)]
    assert all(point.precision != "VERIFIED" for point in result.polyline)
    assert result.coordinate_version == "synthetic-campus-v1"
    assert result.evidence_kind == "SYNTHETIC_FIXTURE" and result.observed_at is not None


@pytest.mark.parametrize("mode", ["MOTORBIKE", "BUS"])
def test_unsupported_mode_returns_without_http(mode):
    provider_type = ors_provider_type()
    requests = []
    transport = httpx.MockTransport(
        lambda request: requests.append(request) or httpx.Response(200, json=route_fixture())
    )
    provider = make_provider(
        provider_type,
        open_settings(
            api_key="",
            include_policy=False,
            enabled=False,
            live_enabled=False,
            routing_provider="disabled",
            ors_base_url="",
        ),
        transport,
    )
    departure_time = datetime(2026, 10, 5, 12, tzinfo=timezone(timedelta(hours=7))) if mode == "BUS" else None

    result = asyncio.run(provider.compute_route(route_request(mode, departure_time=departure_time)))

    assert result.provider == "ors" and result.status == "UNSUPPORTED_MODE"
    assert result.requested_mode == mode and result.effective_mode is None
    assert result.duration_seconds is None and result.distance_meters is None and result.polyline is None
    assert result.observed_at is None and result.evidence_kind == "NONE"
    assert requests == []


def test_provider_instances_consume_the_same_settings_gate_budget():
    provider_type = ors_provider_type()
    requests = []
    transport = httpx.MockTransport(
        lambda request: requests.append(request) or httpx.Response(200, json=route_fixture())
    )
    settings = open_settings(max_requests=1)
    clock = FakeClock()
    first = make_provider(provider_type, settings, transport, clock)
    second = make_provider(provider_type, settings, transport, clock)

    first_result, second_result = asyncio.run(_compute_twice(first, second))

    assert first_result.status == "OK"
    assert second_result.status == "RATE_LIMITED"
    assert second_result.duration_seconds is None and second_result.distance_meters is None
    assert second_result.polyline is None
    assert len(requests) == 1


async def _compute_twice(first, second):
    first_result = await first.compute_route(route_request("WALK"))
    second_result = await second.compute_route(route_request("WALK"))
    return first_result, second_result


def test_missing_server_key_returns_not_configured_without_http():
    provider_type = ors_provider_type()
    requests = []
    transport = httpx.MockTransport(
        lambda request: requests.append(request) or httpx.Response(200, json=route_fixture())
    )
    provider = make_provider(provider_type, open_settings(api_key=""), transport)

    result = asyncio.run(provider.compute_route(route_request("WALK")))

    assert result.status == "NOT_CONFIGURED"
    assert result.evidence_kind == "NONE" and result.observed_at is None
    assert result.duration_seconds is None and result.distance_meters is None and result.polyline is None
    assert requests == []


def test_unapproved_route_capability_returns_without_http():
    provider_type = ors_provider_type()
    requests = []
    transport = httpx.MockTransport(
        lambda request: requests.append(request) or httpx.Response(200, json=route_fixture())
    )
    settings = open_settings(allowed_capabilities=("route:WALK",))
    provider = make_provider(provider_type, settings, transport)

    result = asyncio.run(provider.compute_route(route_request("BICYCLE")))

    assert result.status == "CAPABILITY_UNVERIFIED"
    assert result.evidence_kind == "NONE" and result.observed_at is None
    assert result.duration_seconds is None and result.distance_meters is None and result.polyline is None
    assert result.attribution == []
    assert requests == []


@pytest.mark.parametrize(
    "fixture_name",
    ["route_no_route.json", "route_no_route_between.json"],
)
def test_explicit_ors_no_route_message_maps_to_no_route(fixture_name):
    provider_type = ors_provider_type()
    transport = httpx.MockTransport(
        lambda request: httpx.Response(400, json=load_fixture(fixture_name))
    )
    provider = make_provider(provider_type, open_settings(), transport)

    result = asyncio.run(provider.compute_route(route_request("WALK")))

    assert result.status == "NO_ROUTE"
    assert result.effective_mode is None
    assert result.duration_seconds is None and result.distance_meters is None and result.polyline is None
    assert result.evidence_kind == "SYNTHETIC_FIXTURE" and result.observed_at is not None


def test_empty_success_collection_is_malformed_not_no_route():
    provider_type = ors_provider_type()
    transport = httpx.MockTransport(
        lambda request: httpx.Response(200, json={"type": "FeatureCollection", "features": []})
    )
    provider = make_provider(provider_type, open_settings(), transport)

    result = asyncio.run(provider.compute_route(route_request("WALK")))

    assert result.status == "PROVIDER_ERROR"
    assert result.duration_seconds is None and result.distance_meters is None and result.polyline is None
    assert result.evidence_kind == "SYNTHETIC_FIXTURE" and result.observed_at is not None


@pytest.mark.parametrize(
    "status,expected",
    [(429, "RATE_LIMITED"), (206, "PROVIDER_ERROR"), (403, "PROVIDER_ERROR"), (503, "PROVIDER_ERROR")],
)
def test_http_errors_have_status_and_null_measurements(status, expected):
    provider_type = ors_provider_type()
    transport = httpx.MockTransport(
        lambda request: httpx.Response(
            status,
            json=route_fixture() if status == 206 else {"error": {"message": "Synthetic failure"}},
        )
    )
    provider = make_provider(provider_type, open_settings(), transport)

    result = asyncio.run(provider.compute_route(route_request("WALK")))

    assert result.status == expected
    assert result.effective_mode is None
    assert result.duration_seconds is None and result.distance_meters is None and result.polyline is None
    assert result.evidence_kind == "SYNTHETIC_FIXTURE" and result.observed_at is not None


@pytest.mark.parametrize(
    "case",
    ["negative-distance", "invalid-duration", "nan-duration", "huge-duration", "out-of-range-point", "one-point-line", "missing-summary"],
)
def test_malformed_or_partial_route_response_has_no_measurements(case):
    provider_type = ors_provider_type()
    payload = route_fixture()
    feature = payload["features"][0]
    summary = feature["properties"]["summary"]
    if case == "negative-distance":
        summary["distance"] = -1
    elif case == "invalid-duration":
        summary["duration"] = "372.5s"
    elif case == "nan-duration":
        summary["duration"] = float("nan")
    elif case == "huge-duration":
        summary["duration"] = 10 ** 1000
    elif case == "out-of-range-point":
        feature["geometry"]["coordinates"][0][0] = 181
    elif case == "one-point-line":
        feature["geometry"]["coordinates"] = [[105.77, 10.01]]
    else:
        del feature["properties"]["summary"]
    content = json.dumps(payload).encode("utf-8")
    transport = httpx.MockTransport(
        lambda request: httpx.Response(200, content=content, headers={"Content-Type": "application/json"})
    )
    provider = make_provider(provider_type, open_settings(), transport)

    try:
        result = asyncio.run(provider.compute_route(route_request("WALK")))
    except Exception:
        result = None

    assert result is not None and result.status == "PROVIDER_ERROR"
    assert result.effective_mode is None
    assert result.duration_seconds is None and result.distance_meters is None and result.polyline is None
    assert result.evidence_kind == "SYNTHETIC_FIXTURE" and result.observed_at is not None


def test_unknown_provider_error_code_is_not_classified_as_no_route():
    provider_type = ors_provider_type()
    transport = httpx.MockTransport(
        lambda request: httpx.Response(
            400,
            json={"error": {"code": 9999, "message": "Synthetic upstream failure"}},
        )
    )
    provider = make_provider(provider_type, open_settings(), transport)

    result = asyncio.run(provider.compute_route(route_request("WALK")))

    assert result.status == "PROVIDER_ERROR"
    assert result.duration_seconds is None and result.distance_meters is None and result.polyline is None


def test_no_route_wording_on_success_status_is_not_no_route():
    provider_type = ors_provider_type()
    transport = httpx.MockTransport(
        lambda request: httpx.Response(200, json={"error": {"message": "Route could not be found"}})
    )
    provider = make_provider(provider_type, open_settings(), transport)

    result = asyncio.run(provider.compute_route(route_request("WALK")))

    assert result.status == "PROVIDER_ERROR"


def test_oversized_json_integer_token_is_provider_error_not_exception():
    provider_type = ors_provider_type()
    digits = b"9" * 5000
    body = (
        b'{"type":"FeatureCollection","features":[{"properties":{"summary":{"distance":' +
        digits +
        b',"duration":372.5},"geometry":{"type":"LineString","coordinates":'
        b'[[105.77,10.01],[105.76,10.03]]}}}]}'
    )
    assert len(body) < 1_048_576
    transport = httpx.MockTransport(
        lambda request: httpx.Response(200, content=body, headers={"Content-Type": "application/json"})
    )
    provider = make_provider(provider_type, open_settings(), transport)

    try:
        result = asyncio.run(provider.compute_route(route_request("WALK")))
    except ValueError:
        result = None

    assert result is not None and result.status == "PROVIDER_ERROR"
    assert result.duration_seconds is None and result.distance_meters is None and result.polyline is None
    assert result.evidence_kind == "SYNTHETIC_FIXTURE" and result.observed_at is not None


def test_deeply_nested_non_route_error_body_is_provider_error_not_exception():
    provider_type = ors_provider_type()
    body = b"[" * 2000 + b"0" + b"]" * 2000
    assert len(body) < 1_048_576
    transport = httpx.MockTransport(
        lambda request: httpx.Response(400, content=body, headers={"Content-Type": "application/json"})
    )
    provider = make_provider(provider_type, open_settings(), transport)

    try:
        result = asyncio.run(provider.compute_route(route_request("WALK")))
    except RecursionError:
        result = None

    assert result is not None and result.status == "PROVIDER_ERROR"
    assert result.duration_seconds is None and result.distance_meters is None and result.polyline is None
    assert result.evidence_kind == "SYNTHETIC_FIXTURE" and result.observed_at is not None


def test_transport_failure_is_sanitized_and_not_retried():
    provider_type = ors_provider_type()
    attempts = []

    def fail(request):
        attempts.append(request)
        raise httpx.ConnectError("synthetic-private-host")

    provider = make_provider(provider_type, open_settings(), httpx.MockTransport(fail))

    result = asyncio.run(provider.compute_route(route_request("WALK")))

    assert result.status == "PROVIDER_ERROR"
    assert result.duration_seconds is None and result.distance_meters is None and result.polyline is None
    assert "synthetic-private-host" not in result.model_dump_json()
    assert ORS_SECRET not in result.model_dump_json()
    assert len(attempts) == 1


def test_gate_deadline_after_transport_response_drops_measurements():
    provider_type = ors_provider_type()
    attempts = []
    clock = FakeClock()

    def delayed(request):
        attempts.append(request)
        clock.elapsed = 11.0
        return httpx.Response(200, json=route_fixture())

    provider = make_provider(provider_type, open_settings(), httpx.MockTransport(delayed), clock)

    result = asyncio.run(provider.compute_route(route_request("WALK")))

    assert result.status == "PROVIDER_ERROR"
    assert result.duration_seconds is None and result.distance_meters is None and result.polyline is None
    assert result.evidence_kind == "NONE" and result.observed_at is None
    assert len(attempts) == 1


def test_oversized_response_is_rejected_by_gate_without_retry():
    provider_type = ors_provider_type()
    attempts = []

    def oversized(request):
        attempts.append(request)
        return httpx.Response(200, content=b"x" * 1_048_577)

    provider = make_provider(provider_type, open_settings(), httpx.MockTransport(oversized))

    result = asyncio.run(provider.compute_route(route_request("WALK")))

    assert result.status == "PROVIDER_ERROR"
    assert result.duration_seconds is None and result.distance_meters is None and result.polyline is None
    assert result.evidence_kind == "NONE" and result.observed_at is None
    assert len(attempts) == 1


def load_fixture(name):
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))
