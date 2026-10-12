"""P0 open-mobility settings, registry and request-policy contracts."""
import asyncio
from datetime import datetime, timedelta, timezone
import hashlib
import importlib

import httpx
import pytest
from pydantic import SecretStr, ValidationError


_POLICY_BYTES = (
    b'{"allowed_capabilities":["nearby"],"allowed_paths":["/api/interpreter"],'
    b'"approved_until":"2026-10-06T00:00:00Z",'
    b'"attribution":["\xc2\xa9 OpenStreetMap contributors"],'
    b'"base_url":"https://overpass.example.test",'
    b'"cache_policy":"NO_CACHE_ALLOWED","connect_timeout_seconds":2.0,'
    b'"max_concurrency":1,"max_requests":1,"max_response_bytes":1048576,'
    b'"max_rps":1.0,"provider":"osm_overpass","timeout_seconds":10.0,'
    b'"user_agent":"NCKH mobility policy test"}'
)
_POLICY_SHA256 = "b7d6bce95f340bcc446b633e5451f6a60550f30cf68bbe500abccdf93b6d3ae1"
_EXPIRED_POLICY_SHA256 = "8000ee0853bd83105120ecd98d5e3495a35fd15265b9d9ccbefc0be9631731e0"
_ORS_POLICY_SHA256 = "6f8a7d2ebce95a33f9a7fd7a44f6752aa6b14943396b3314f2dc38087a8cfb33"
_TWO_REQUESTS_POLICY_SHA256 = "d06721e2c17ade788f5ed42066ae2eb95c288c94ac17ca408d35ffe3fb52b52a"
_THREE_REQUESTS_POLICY_SHA256 = "56e4534ecd024286459d60d1b95ddc585c12a901bd9e6b7cd3a6e435ab808ec9"


def feature_module(name):
    """Turn a missing P0 module into a named assertion failure, not collection error."""
    try:
        return importlib.import_module(name)
    except ModuleNotFoundError as exc:
        pytest.fail(f"P0 module {name} is required; missing {exc.name}")


def open_settings(**values):
    return feature_module("app.mobility.providers.open_config").OpenMobilitySettings(
        _env_file=None, **values
    )


def policy(network, **overrides):
    values = {
        "provider": "osm_overpass",
        "base_url": "https://overpass.example.test",
        "allowed_paths": ("/api/interpreter",),
        "allowed_capabilities": ("nearby",),
        "attribution": ("© OpenStreetMap contributors",),
        "user_agent": "NCKH mobility policy test",
        "cache_policy": "NO_CACHE_ALLOWED",
        "policy_sha256": _POLICY_SHA256,
        "approved_until": datetime(2026, 10, 6, tzinfo=timezone.utc),
        "max_requests": 1,
        "max_rps": 1.0,
        "max_concurrency": 1,
        "timeout_seconds": 10.0,
        "connect_timeout_seconds": 2.0,
        "max_response_bytes": 1_048_576,
    }
    values.update(overrides)
    return network.ProviderPolicy(**values)


class FakeClock:
    def __init__(self, now=None):
        self.now = now or datetime(2026, 10, 5, 12, tzinfo=timezone.utc)
        self.elapsed = 0.0

    def monotonic(self):
        return self.elapsed

    def utcnow(self):
        return self.now

    async def sleep(self, seconds):
        self.elapsed += seconds
        self.now += timedelta(seconds=seconds)
        await asyncio.sleep(0)


class RealScheduleClock:
    def monotonic(self):
        return asyncio.get_running_loop().time()

    def utcnow(self):
        return datetime(2026, 10, 5, 12, tzinfo=timezone.utc)

    async def sleep(self, seconds):
        await asyncio.sleep(seconds)


async def public_resolver(_host):
    return ("93.184.216.34",)


def gate(network, *, policy_value=None, expected_hash=None, live_enabled=True,
         transport=None, resolver=public_resolver, clock=None, server_credentials=None):
    policy_value = policy_value or policy(network)
    return network.RequestPolicyGate(
        policies={"osm_overpass": policy_value},
        expected_policy_hashes={"osm_overpass": expected_hash or _POLICY_SHA256},
        live_enabled=live_enabled,
        transport=transport,
        resolver=resolver,
        clock=clock or FakeClock(),
        server_credentials=server_credentials,
    )


async def attempt_send(network, request_gate):
    try:
        async with request_gate.claim("osm_overpass", "nearby", "/api/interpreter") as permit:
            response = await permit.send("POST", form={"data": "fixture query"})
            return "SENT", response
    except network.RequestPolicyError as exc:
        return exc.status, None


def test_open_provider_defaults_are_off_and_secret_is_redacted():
    config = open_settings(ors_api_key="sentinel-ors-secret")

    assert config.enabled is False
    assert config.live_enabled is False
    assert config.google_maps_enabled is False
    assert config.routing_provider == "disabled"
    assert config.places_provider == "disabled"
    assert config.geocoder_provider == "disabled"
    assert config.ors_base_url == ""
    assert config.overpass_url == ""
    assert config.nominatim_url == ""
    assert config.tiles_enabled is False
    assert "sentinel-ors-secret" not in repr(config)


def test_exact_google_maps_environment_switch_is_rejected(monkeypatch):
    monkeypatch.setenv("GOOGLE_MAPS_ENABLED", "true")

    with pytest.raises(ValidationError):
        feature_module("app.mobility.providers.open_config").OpenMobilitySettings(_env_file=None)


def test_settings_bind_one_gate_to_one_constructor_transport():
    network = feature_module("app.mobility.providers.network_policy")
    config_type = feature_module("app.mobility.providers.open_config").OpenMobilitySettings
    provider_policy = policy(network)
    settings = config_type(
        _env_file=None,
        enabled=True,
        live_enabled=True,
        overpass_url="https://overpass.example.test/api/interpreter",
        provider_policies={"osm_overpass": provider_policy},
        expected_policy_hashes={"osm_overpass": _POLICY_SHA256},
    )
    calls = []
    first_transport = httpx.MockTransport(
        lambda request: calls.append(request) or httpx.Response(200, request=request)
    )
    other_transport = httpx.MockTransport(lambda request: httpx.Response(200, request=request))
    clock = FakeClock()

    first = settings.get_request_policy_gate(
        transport=first_transport, resolver=public_resolver, clock=clock,
    )
    same = settings.get_request_policy_gate(
        transport=first_transport, resolver=public_resolver, clock=clock,
    )

    assert first is same
    assert settings.request_policy_gate is first
    with pytest.raises(ValueError):
        settings.get_request_policy_gate(transport=other_transport)

    async def send_twice():
        return await attempt_send(network, first), await attempt_send(network, same)

    outcomes = [status for status, _ in asyncio.run(send_twice())]
    assert outcomes == ["SENT", "RATE_LIMITED"]
    assert len(calls) == 1


@pytest.mark.parametrize("field,value", [
    ("routing_provider", "google"),
    ("places_provider", "google"),
    ("geocoder_provider", "google"),
    ("routing_provider", "surprise"),
])
def test_open_provider_settings_reject_google_and_unknown_names(field, value):
    with pytest.raises(ValidationError):
        open_settings(**{field: value})


def test_registry_returns_neutral_results_without_implicitly_loading_google():
    registry = feature_module("app.mobility.providers.registry")
    contracts = feature_module("app.mobility.contracts")
    config = open_settings()
    route_provider = registry.build_route_provider(config)
    places_provider = registry.build_places_provider(config)
    route_request = contracts.ResolvedRouteRequest(
        request=contracts.RouteRequest(listing_id=1, campus_id="khu_ii", requested_mode="WALK"),
        origin=contracts.Position(lat=10.01, lng=105.77),
        destination=contracts.Campus(
            id="khu_ii", name="Synthetic campus", lat=10.03, lng=105.76,
            coordinate_version="fixture-v1", verification_status="PROVISIONAL",
        ),
    )
    nearby_request = contracts.ResolvedNearbyRequest(
        request=contracts.NearbyRequest(listing_id=1, categories=["police"]),
        center=contracts.Position(lat=10.01, lng=105.77),
    )

    route = asyncio.run(route_provider.compute_route(route_request))
    nearby = asyncio.run(places_provider.nearby(nearby_request))

    assert (route.provider, route.status, route.evidence_kind) == ("none", "NOT_CONFIGURED", "NONE")
    assert route.duration_seconds is None and route.distance_meters is None and route.polyline is None
    assert (nearby.provider, nearby.status, nearby.evidence_kind) == ("none", "NOT_CONFIGURED", "NONE")
    assert nearby.items == [] and nearby.coverage == "UNKNOWN"


def test_selected_open_provider_without_its_adapter_fails_closed(monkeypatch):
    import sys

    registry = feature_module("app.mobility.providers.registry")
    monkeypatch.setitem(sys.modules, "app.mobility.providers.ors_routes", None)
    provider = registry.build_route_provider(open_settings(routing_provider="ors"))
    contracts = feature_module("app.mobility.contracts")
    request = contracts.ResolvedRouteRequest(
        request=contracts.RouteRequest(listing_id=1, campus_id="khu_ii", requested_mode="WALK"),
        origin=contracts.Position(lat=10.01, lng=105.77),
        destination=contracts.Campus(
            id="khu_ii", name="Synthetic campus", lat=10.03, lng=105.76,
            coordinate_version="fixture-v1", verification_status="PROVISIONAL",
        ),
    )

    result = asyncio.run(provider.compute_route(request))

    assert result.status == "CAPABILITY_UNVERIFIED"
    assert result.provider == "ors"
    assert result.duration_seconds is None and result.distance_meters is None


def test_provider_policy_digest_matches_independent_canonical_bytes_vector():
    network = feature_module("app.mobility.providers.network_policy")
    assert hashlib.sha256(_POLICY_BYTES).hexdigest() == _POLICY_SHA256

    assert network.policy_digest(policy(network)) == _POLICY_SHA256


def test_self_declared_or_stale_policy_hash_never_becomes_trusted():
    network = feature_module("app.mobility.providers.network_policy")
    calls = []
    transport = httpx.MockTransport(lambda request: calls.append(request) or httpx.Response(200))
    changed = policy(network, user_agent="changed without a new approval")
    request_gate = gate(network, policy_value=changed, transport=transport)

    status, response = asyncio.run(attempt_send(network, request_gate))

    assert status == "CAPABILITY_UNVERIFIED"
    assert response is None
    assert calls == []


def test_live_off_missing_expired_or_private_policy_never_sends():
    network = feature_module("app.mobility.providers.network_policy")
    calls = []
    transport = httpx.MockTransport(lambda request: calls.append(request) or httpx.Response(200))

    disabled = gate(network, live_enabled=False, transport=transport)
    expired_policy = policy(
        network,
        policy_sha256=_EXPIRED_POLICY_SHA256,
        approved_until=datetime(2026, 10, 5, 11, tzinfo=timezone.utc),
    )
    expired = gate(network, policy_value=expired_policy, expected_hash=_EXPIRED_POLICY_SHA256,
                   transport=transport)

    async def private_resolver(_host):
        return ("192.168.1.9",)

    private = gate(network, transport=transport, resolver=private_resolver)

    outcomes = [
        asyncio.run(attempt_send(network, disabled))[0],
        asyncio.run(attempt_send(network, expired))[0],
        asyncio.run(attempt_send(network, private))[0],
    ]

    assert outcomes == ["NOT_CONFIGURED", "CAPABILITY_UNVERIFIED", "CAPABILITY_UNVERIFIED"]
    assert calls == []


def test_policy_record_and_input_mappings_cannot_be_mutated_to_reset_trust():
    network = feature_module("app.mobility.providers.network_policy")
    policy_value = policy(network)
    policies = {"osm_overpass": policy_value}
    expected_hashes = {"osm_overpass": _POLICY_SHA256}
    calls = []
    transport = httpx.MockTransport(
        lambda request: calls.append(request) or httpx.Response(200, content=b"ok", request=request)
    )
    request_gate = network.RequestPolicyGate(
        policies=policies,
        expected_policy_hashes=expected_hashes,
        live_enabled=True,
        transport=transport,
        resolver=public_resolver,
        clock=FakeClock(),
    )
    policies.clear()
    expected_hashes.clear()
    with pytest.raises(ValidationError):
        policy_value.base_url = "https://attacker.example.test"

    status, response = asyncio.run(attempt_send(network, request_gate))

    assert status == "SENT"
    assert response.evidence_kind == "SYNTHETIC_FIXTURE"
    assert len(calls) == 1


def test_missing_or_self_declared_expected_hash_is_not_an_approval():
    network = feature_module("app.mobility.providers.network_policy")
    policy_value = policy(network, policy_sha256="0" * 64)
    calls = []
    transport = httpx.MockTransport(
        lambda request: calls.append(request) or httpx.Response(200, request=request)
    )
    missing = network.RequestPolicyGate(
        policies={"osm_overpass": policy(network)},
        expected_policy_hashes={},
        live_enabled=True,
        transport=transport,
        resolver=public_resolver,
        clock=FakeClock(),
    )
    self_declared = gate(
        network,
        policy_value=policy_value,
        expected_hash="0" * 64,
        transport=transport,
    )

    outcomes = [
        asyncio.run(attempt_send(network, missing))[0],
        asyncio.run(attempt_send(network, self_declared))[0],
    ]

    assert outcomes == ["CAPABILITY_UNVERIFIED", "CAPABILITY_UNVERIFIED"]
    assert calls == []


def test_atomic_request_budget_allows_only_one_concurrent_send():
    network = feature_module("app.mobility.providers.network_policy")
    calls = []
    entered = asyncio.Event()
    release = asyncio.Event()

    async def handler(request):
        calls.append(request)
        entered.set()
        await release.wait()
        return httpx.Response(200, content=b"ok", request=request)

    request_gate = gate(network, transport=httpx.MockTransport(handler))

    async def run_pair():
        async def attempt():
            return await attempt_send(network, request_gate)

        first = asyncio.create_task(attempt())
        await entered.wait()
        second = asyncio.create_task(attempt())
        await asyncio.sleep(0)
        release.set()
        return await asyncio.gather(first, second)

    outcomes = asyncio.run(run_pair())

    assert sorted(outcome[0] for outcome in outcomes) == ["RATE_LIMITED", "SENT"]
    sent = next(response for status, response in outcomes if status == "SENT")
    assert sent.evidence_kind == "SYNTHETIC_FIXTURE"
    assert len(calls) == 1


def test_failed_transport_attempt_consumes_the_shared_request_budget():
    network = feature_module("app.mobility.providers.network_policy")
    calls = []

    def fail(request):
        calls.append(request)
        raise httpx.ConnectError("synthetic transport failure")

    request_gate = gate(network, transport=httpx.MockTransport(fail))

    async def run_twice():
        return await attempt_send(network, request_gate), await attempt_send(network, request_gate)

    first, second = asyncio.run(run_twice())

    assert first[0] == "PROVIDER_ERROR"
    assert second[0] == "RATE_LIMITED"
    assert len(calls) == 1


def test_dns_and_response_body_are_inside_the_ten_second_deadline():
    network = feature_module("app.mobility.providers.network_policy")
    calls = []
    dns_clock = FakeClock()

    async def slow_resolver(_host):
        await dns_clock.sleep(11)
        return ("93.184.216.34",)

    dns_gate = gate(
        network,
        transport=httpx.MockTransport(
            lambda request: calls.append(request) or httpx.Response(200, request=request)
        ),
        resolver=slow_resolver,
        clock=dns_clock,
    )
    dns_status, _ = asyncio.run(attempt_send(network, dns_gate))

    body_clock = FakeClock()

    class SlowBody(httpx.AsyncByteStream):
        async def __aiter__(self):
            await body_clock.sleep(11)
            yield b"late"

        async def aclose(self):
            return None

    body_gate = gate(
        network,
        transport=httpx.MockTransport(
            lambda request: httpx.Response(200, stream=SlowBody(), request=request)
        ),
        clock=body_clock,
    )
    body_status, _ = asyncio.run(attempt_send(network, body_gate))

    assert dns_status == "PROVIDER_ERROR"
    assert body_status == "PROVIDER_ERROR"
    assert calls == []


def test_permit_cannot_send_after_context_exit_or_send_twice():
    network = feature_module("app.mobility.providers.network_policy")
    calls = []
    request_gate = gate(
        network,
        transport=httpx.MockTransport(
            lambda request: calls.append(request) or httpx.Response(200, request=request)
        ),
    )

    async def run():
        async with request_gate.claim("osm_overpass", "nearby", "/api/interpreter") as permit:
            first = await permit.send("POST", form={"data": "fixture query"})
            try:
                await permit.send("POST", form={"data": "second query"})
            except network.RequestPolicyError as exc:
                second_status = exc.status
            else:
                second_status = "SENT"
        try:
            await permit.send("POST", form={"data": "after context"})
        except network.RequestPolicyError as exc:
            after_exit_status = exc.status
        else:
            after_exit_status = "SENT"
        return first, second_status, after_exit_status

    first, second_status, after_exit_status = asyncio.run(run())

    assert first.evidence_kind == "SYNTHETIC_FIXTURE"
    assert second_status == "PROVIDER_ERROR"
    assert after_exit_status == "PROVIDER_ERROR"
    assert len(calls) == 1


def test_two_allowed_requests_start_at_least_one_second_apart():
    network = feature_module("app.mobility.providers.network_policy")
    policy_value = policy(
        network,
        max_requests=2,
        policy_sha256=_TWO_REQUESTS_POLICY_SHA256,
    )
    clock = FakeClock()
    send_times = []

    def handler(request):
        send_times.append(clock.monotonic())
        return httpx.Response(200, content=b"ok", request=request)

    request_gate = gate(
        network,
        policy_value=policy_value,
        expected_hash=_TWO_REQUESTS_POLICY_SHA256,
        transport=httpx.MockTransport(handler),
        clock=clock,
    )
    async def run_twice():
        return [await attempt_send(network, request_gate), await attempt_send(network, request_gate)]

    outcomes = [status for status, _ in asyncio.run(run_twice())]

    assert outcomes == ["SENT", "SENT"]
    assert send_times[1] - send_times[0] >= 1.0


def test_queued_requests_measure_rate_from_actual_send_start():
    network = feature_module("app.mobility.providers.network_policy")
    policy_value = policy(
        network,
        max_requests=3,
        policy_sha256=_THREE_REQUESTS_POLICY_SHA256,
    )
    started = asyncio.Event()
    release_first = asyncio.Event()
    send_times = []

    async def handler(request):
        now = asyncio.get_running_loop().time()
        send_times.append(now)
        if len(send_times) == 1:
            started.set()
            await release_first.wait()
        return httpx.Response(200, content=b"ok", request=request)

    request_gate = gate(
        network,
        policy_value=policy_value,
        expected_hash=_THREE_REQUESTS_POLICY_SHA256,
        transport=httpx.MockTransport(handler),
        clock=RealScheduleClock(),
    )

    async def run_queued():
        first = asyncio.create_task(attempt_send(network, request_gate))
        await started.wait()
        second = asyncio.create_task(attempt_send(network, request_gate))
        await asyncio.sleep(0.05)
        third = asyncio.create_task(attempt_send(network, request_gate))
        await asyncio.sleep(1.7)
        release_first.set()
        return await asyncio.gather(first, second, third)

    outcomes = asyncio.run(run_queued())

    assert [status for status, _ in outcomes] == ["SENT", "SENT", "SENT"]
    assert len(send_times) == 3
    assert all(later - earlier >= 1.0 for earlier, later in zip(send_times, send_times[1:]))


def test_response_cap_and_redirects_become_provider_errors_without_followup_send():
    network = feature_module("app.mobility.providers.network_policy")
    seen = []

    def redirect_handler(request):
        seen.append(request.url)
        return httpx.Response(302, headers={"Location": "https://private.example.test/secret"}, request=request)

    redirect_gate = gate(network, transport=httpx.MockTransport(redirect_handler))
    redirect_status, _ = asyncio.run(attempt_send(network, redirect_gate))

    large_policy = policy(network)
    large_gate = gate(
        network,
        policy_value=large_policy,
        transport=httpx.MockTransport(
            lambda request: httpx.Response(
                200, content=b"x" * 1_048_577, request=request,
            )
        ),
    )
    size_status, _ = asyncio.run(attempt_send(network, large_gate))

    assert redirect_status == "PROVIDER_ERROR"
    assert size_status == "PROVIDER_ERROR"
    assert seen == [httpx.URL("https://overpass.example.test/api/interpreter")]


def test_permit_rejects_non_allowlisted_path_before_transport():
    network = feature_module("app.mobility.providers.network_policy")
    calls = []
    request_gate = gate(
        network,
        transport=httpx.MockTransport(lambda request: calls.append(request) or httpx.Response(200)),
    )

    async def request_wrong_path():
        try:
            async with request_gate.claim("osm_overpass", "nearby", "/api/interpreter/extra") as permit:
                await permit.send("POST", form={"data": "fixture query"})
        except network.RequestPolicyError as exc:
            return exc.status
        return "SENT"

    assert asyncio.run(request_wrong_path()) == "CAPABILITY_UNVERIFIED"
    assert calls == []


def test_private_settings_host_and_nonexact_policy_path_are_rejected():
    network = feature_module("app.mobility.providers.network_policy")
    config_module = feature_module("app.mobility.providers.open_config")

    with pytest.raises(ValidationError):
        config_module.OpenMobilitySettings(_env_file=None, overpass_url="https://127.0.0.1/api/interpreter")
    with pytest.raises(ValidationError):
        policy(network, base_url="http://overpass.example.test")
    with pytest.raises(ValidationError):
        policy(network, base_url="https://127.0.0.1")
    with pytest.raises(ValidationError):
        policy(network, allowed_paths=("/api/*",))


def test_settings_policy_endpoint_path_must_match_approved_endpoint_before_send():
    network = feature_module("app.mobility.providers.network_policy")
    config_module = feature_module("app.mobility.providers.open_config")
    calls = []
    transport = httpx.MockTransport(
        lambda request: calls.append(request) or httpx.Response(200, request=request)
    )
    settings = config_module.OpenMobilitySettings(
        _env_file=None,
        enabled=True,
        live_enabled=True,
        places_provider="osm_overpass",
        overpass_url="https://overpass.example.test/not-approved",
        provider_policies={"osm_overpass": policy(network)},
        expected_policy_hashes={"osm_overpass": _POLICY_SHA256},
    )
    request_gate = settings.get_request_policy_gate(
        transport=transport,
        resolver=public_resolver,
        clock=FakeClock(),
    )
    status, response = asyncio.run(attempt_send(network, request_gate))

    assert status == "CAPABILITY_UNVERIFIED"
    assert response is None
    assert calls == []


def test_ors_secret_is_in_authorization_only_and_missing_key_sends_nothing():
    network = feature_module("app.mobility.providers.network_policy")
    ors_policy = network.ProviderPolicy(
        provider="ors",
        base_url="https://api.openrouteservice.org",
        allowed_paths=("/v2/directions/foot-walking/geojson",),
        allowed_capabilities=("route:WALK",),
        attribution=("OpenRouteService",),
        user_agent="NCKH mobility policy test",
        cache_policy="NO_CACHE_ALLOWED",
        policy_sha256=_ORS_POLICY_SHA256,
        approved_until=datetime(2026, 10, 6, tzinfo=timezone.utc),
        max_requests=1,
        max_rps=1.0,
        max_concurrency=1,
        timeout_seconds=10.0,
        connect_timeout_seconds=2.0,
        max_response_bytes=1_048_576,
    )
    requests = []

    def handler(request):
        requests.append(request)
        return httpx.Response(200, content=b"{}", request=request)

    transport = httpx.MockTransport(handler)
    authorized_gate = network.RequestPolicyGate(
        policies={"ors": ors_policy},
        expected_policy_hashes={"ors": _ORS_POLICY_SHA256},
        live_enabled=True,
        transport=transport,
        resolver=public_resolver,
        clock=FakeClock(),
        server_credentials={"ors": SecretStr("sentinel-ors-secret")},
    )

    async def post_route(request_gate):
        try:
            async with request_gate.claim(
                "ors", "route:WALK", "/v2/directions/foot-walking/geojson"
            ) as permit:
                response = await permit.send(
                    "POST", json_body={"coordinates": [[105.77, 10.01], [105.76, 10.03]]}
                )
                return "SENT", response
        except network.RequestPolicyError as exc:
            return exc.status, None

    status, response = asyncio.run(post_route(authorized_gate))
    assert status == "SENT"
    assert response.evidence_kind == "SYNTHETIC_FIXTURE"
    assert len(requests) == 1
    assert requests[0].headers["Authorization"] == "sentinel-ors-secret"
    assert "sentinel-ors-secret" not in str(requests[0].url)
    assert "sentinel-ors-secret" not in requests[0].content.decode("utf-8")
    assert "sentinel-ors-secret" not in repr(authorized_gate)

    missing_key_gate = network.RequestPolicyGate(
        policies={"ors": ors_policy},
        expected_policy_hashes={"ors": _ORS_POLICY_SHA256},
        live_enabled=True,
        transport=transport,
        resolver=public_resolver,
        clock=FakeClock(),
    )
    denied_status, denied_response = asyncio.run(post_route(missing_key_gate))
    assert denied_status == "NOT_CONFIGURED"
    assert denied_response is None
    assert len(requests) == 1
