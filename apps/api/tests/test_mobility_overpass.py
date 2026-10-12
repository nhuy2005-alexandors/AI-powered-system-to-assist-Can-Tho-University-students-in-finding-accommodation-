"""Offline contract checks for the bounded Overpass places adapter."""
import asyncio
from datetime import datetime, timedelta, timezone
import hashlib
import importlib
import json
from pathlib import Path
from urllib.parse import parse_qs

import httpx
import pytest

from app.mobility.contracts import NearbyRequest, Position, ResolvedNearbyRequest


FIXTURES = Path(__file__).parent / "fixtures/open_mobility/overpass"
_POLICY_BYTES = (
    b'{"allowed_capabilities":["nearby"],"allowed_paths":["/api/interpreter"],'
    b'"approved_until":"2026-10-06T00:00:00Z",'
    b'"attribution":["\xc2\xa9 OpenStreetMap contributors"],'
    b'"base_url":"https://overpass.example.test",'
    b'"cache_policy":"NO_CACHE_ALLOWED","connect_timeout_seconds":2.0,'
    b'"max_concurrency":1,"max_requests":1,"max_response_bytes":1048576,'
    b'"max_rps":1.0,"provider":"osm_overpass","timeout_seconds":10.0,'
    b'"user_agent":"NCKH mobility synthetic fixture tests"}'
)
POLICY_SHA256 = "124b5d29060009f8e8faca7a8638058a2d7d9e426a533c40da491d29891fdd52"


def overpass_module():
    try:
        return importlib.import_module("app.mobility.providers.overpass_places")
    except ModuleNotFoundError as exc:
        pytest.fail(f"Overpass Places adapter is not implemented: {exc.name}")


def overpass_provider(module, settings):
    provider_type = getattr(module, "OverpassPlacesProvider", None)
    assert provider_type is not None, "OverpassPlacesProvider is not implemented"
    return provider_type(settings)


def resolved(*, radius=1000, categories=("bus_stop",), center=(10.0, 105.0)):
    request = NearbyRequest(
        listing_id=7,
        radius_m=radius,
        categories=list(categories),
    )
    position = Position(
        lat=center[0],
        lng=center[1],
        precision="APPROXIMATE",
        source="SYNTHETIC_FIXTURE",
    )
    return ResolvedNearbyRequest(request=request, center=position)


def fixture(name):
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


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


async def public_resolver(host):
    assert host == "overpass.example.test"
    return ("93.184.216.34",)


def configured_settings(
    transport,
    *,
    include_policy=True,
    enabled=True,
    live_enabled=True,
    resolver=public_resolver,
    clock=None,
):
    network = importlib.import_module("app.mobility.providers.network_policy")
    settings_module = importlib.import_module("app.mobility.providers.open_config")
    policy = network.ProviderPolicy(
        provider="osm_overpass",
        base_url="https://overpass.example.test",
        allowed_paths=("/api/interpreter",),
        allowed_capabilities=("nearby",),
        attribution=("© OpenStreetMap contributors",),
        user_agent="NCKH mobility synthetic fixture tests",
        cache_policy="NO_CACHE_ALLOWED",
        policy_sha256=POLICY_SHA256,
        approved_until=datetime(2026, 10, 6, tzinfo=timezone.utc),
        max_requests=1,
        max_rps=1.0,
        max_concurrency=1,
        timeout_seconds=10.0,
        connect_timeout_seconds=2.0,
        max_response_bytes=1_048_576,
    )
    settings = settings_module.OpenMobilitySettings(
        _env_file=None,
        enabled=enabled,
        live_enabled=live_enabled,
        places_provider="osm_overpass",
        overpass_url="https://overpass.example.test/api/interpreter",
        provider_policies={"osm_overpass": policy} if include_policy else {},
        expected_policy_hashes={"osm_overpass": POLICY_SHA256} if include_policy else {},
    )
    gate = settings.get_request_policy_gate(
        transport=transport,
        resolver=resolver,
        clock=clock or FakeClock(),
    )
    return settings, gate


def test_synthetic_policy_hash_matches_an_independent_canonical_byte_vector():
    assert hashlib.sha256(_POLICY_BYTES).hexdigest() == POLICY_SHA256


def test_query_has_only_fixed_category_tags_and_bus_specific_platform_selector():
    module = overpass_module()

    query = module.build_overpass_query(resolved(
        radius=500,
        categories=("grocery", "market", "pharmacy", "healthcare", "police", "bus_stop"),
    ))

    assert query == """[out:json][timeout:8];
(
  nwr(around:500,10.0,105.0)["shop"="supermarket"];
  nwr(around:500,10.0,105.0)["shop"="convenience"];
  nwr(around:500,10.0,105.0)["amenity"="marketplace"];
  nwr(around:500,10.0,105.0)["amenity"="pharmacy"];
  nwr(around:500,10.0,105.0)["amenity"="hospital"];
  nwr(around:500,10.0,105.0)["amenity"="clinic"];
  nwr(around:500,10.0,105.0)["amenity"="doctors"];
  nwr(around:500,10.0,105.0)["amenity"="police"];
  nwr(around:500,10.0,105.0)["highway"="bus_stop"];
  nwr(around:500,10.0,105.0)["public_transport"="platform"]["bus"="yes"];
);
out center 101;"""


def test_nearby_parses_osm_element_types_and_rejects_platform_false_positives():
    module = overpass_module()
    requests = []
    transport = httpx.MockTransport(
        lambda request: requests.append(request) or httpx.Response(
            200, json=fixture("nearby_mixed.json"), request=request
        )
    )
    settings, gate = configured_settings(transport)
    provider = overpass_provider(module, settings)
    request_data = resolved(
        radius=500,
        categories=("bus_stop", "police", "healthcare", "pharmacy", "grocery"),
    )

    result = asyncio.run(provider.nearby(request_data))

    assert settings.request_policy_gate is gate
    assert len(requests) == 1
    assert requests[0].method == "POST"
    assert str(requests[0].url) == "https://overpass.example.test/api/interpreter"
    assert requests[0].headers["Host"] == "overpass.example.test"
    assert parse_qs(requests[0].content.decode("utf-8")) == {
        "data": [module.build_overpass_query(request_data)],
    }
    assert result.status == "OK" and result.coverage == "PARTIAL"
    assert result.provider == "osm_overpass"
    assert result.evidence_kind == "SYNTHETIC_FIXTURE" and result.queried_at is not None
    assert [place.category for place in result.items] == [
        "grocery", "grocery", "pharmacy", "healthcare", "police", "bus_stop",
    ]
    assert [place.provider_place_id for place in result.items] == [
        "node:1", "node:9", "way:1", "relation:3", "relation:4", "node:2",
    ]
    assert all(0 <= place.straight_line_distance_m <= 500 for place in result.items)
    assert result.items[0].name == result.items[1].name
    assert (result.items[0].lat, result.items[0].lng) == (
        result.items[1].lat, result.items[1].lng,
    )
    assert result.items[0].category == "grocery"  # Fixed enum priority for dual-tag elements.
    assert result.items[0].attribution == [
        "© OpenStreetMap contributors",
        "Data licensed under the Open Database License (ODbL)",
        "Overpass endpoint: https://overpass.example.test/api/interpreter",
    ]
    assert set(result.items[0].model_dump()) == {
        "provider_place_id", "name", "category", "lat", "lng",
        "straight_line_distance_m", "attribution",
    }
    encoded = result.model_dump_json()
    for private_value in ("+1-555-0100", "private@example.test", "Synthetic Operator", "secret notes"):
        assert private_value not in encoded
    assert "security_score" not in result.model_dump()


def test_valid_empty_is_observed_but_overpass_remark_and_partial_data_are_not_empty():
    module = overpass_module()

    def observe(*, payload=None, content=None):
        transport = httpx.MockTransport(lambda request: httpx.Response(
            200,
            json=payload if content is None else None,
            content=content,
            request=request,
        ))
        settings, _ = configured_settings(transport)
        return asyncio.run(overpass_provider(module, settings).nearby(
            resolved(categories=("grocery",))
        ))

    empty = observe(payload={"elements": []})
    remark = observe(payload={"remark": "synthetic runtime error", "elements": []})
    nested_partial = observe(payload={
        "osm3s": {"remark": "synthetic partial response"},
        "elements": [],
    })
    malformed = observe(content=b"not-json")
    missing_elements = observe(payload={"version": 0.6})
    long_integer = observe(content=b'{"elements":[],"marker":' + b"9" * 5000 + b"}")
    deeply_nested = observe(
        content=b'{"elements":[],"nested":' + b"[" * 1500 + b"0" + b"]" * 1500 + b"}"
    )

    assert empty.status == "EMPTY"
    assert empty.coverage == "PARTIAL" and empty.evidence_kind == "SYNTHETIC_FIXTURE"
    assert empty.queried_at is not None and empty.items == []
    for result in (
        remark, nested_partial, malformed, missing_elements, long_integer, deeply_nested,
    ):
        assert result.status == "PROVIDER_ERROR"
        assert result.coverage == "UNKNOWN" and result.items == [] and not result.truncated
        assert result.evidence_kind == "SYNTHETIC_FIXTURE" and result.queried_at is not None


def test_explicit_overpass_error_object_is_not_reported_as_empty():
    module = overpass_module()
    transport = httpx.MockTransport(lambda request: httpx.Response(
        200,
        json={"error": {"message": "syntheticfailure"}, "elements": []},
        request=request,
    ))
    settings, _ = configured_settings(transport)

    result = asyncio.run(overpass_provider(module, settings).nearby(
        resolved(categories=("grocery",))
    ))

    assert result.status == "PROVIDER_ERROR"
    assert result.coverage == "UNKNOWN" and result.items == [] and not result.truncated
    assert result.evidence_kind == "SYNTHETIC_FIXTURE" and result.queried_at is not None
    assert "syntheticfailure" not in result.model_dump_json()


def test_endpoint_attribution_uses_approved_policy_not_untrusted_copied_setting():
    module = overpass_module()
    transport = httpx.MockTransport(lambda request: httpx.Response(
        200,
        json={"elements": [{
            "type": "node",
            "id": 41,
            "lat": 10.0001,
            "lon": 105.0,
            "tags": {"shop": "supermarket", "name": "Synthetic Grocery"},
        }]},
        request=request,
    ))
    settings, _ = configured_settings(transport)
    settings = settings.model_copy(update={
        "overpass_url": "https://operator:synthetic-sentinel@overpass.example.test/api/interpreter",
    })

    result = asyncio.run(overpass_provider(module, settings).nearby(
        resolved(categories=("grocery",))
    ))

    assert result.status == "OK"
    serialized = result.model_dump_json()
    assert "synthetic-sentinel" not in serialized
    assert "operator@" not in serialized
    assert result.items[0].attribution[-1] == (
        "Overpass endpoint: https://overpass.example.test/api/interpreter"
    )


def test_overpass_101_element_cap_returns_at_most_100_and_marks_truncated():
    module = overpass_module()
    elements = [
        {
            "type": "node",
            "id": index,
            "lat": 10.0001,
            "lon": 105.0,
            "tags": {"shop": "convenience", "name": f"Synthetic Store {index}"},
        }
        for index in range(1, 102)
    ]
    requests = []
    transport = httpx.MockTransport(
        lambda request: requests.append(request) or httpx.Response(
            200, json={"elements": elements}, request=request
        )
    )
    settings, _ = configured_settings(transport)

    result = asyncio.run(overpass_provider(module, settings).nearby(
        resolved(radius=1000, categories=("grocery",))
    ))

    assert result.status == "OK" and result.coverage == "PARTIAL"
    assert len(result.items) == 100 and result.truncated is True
    assert [place.provider_place_id for place in result.items] == [
        f"node:{index}" for index in range(1, 101)
    ]
    assert len(requests) == 1
    assert requests[0].url.path == "/api/interpreter"
    assert "out center 101;" in parse_qs(requests[0].content.decode("utf-8"))["data"][0]


def test_named_category_without_osm_name_gets_explicit_nonfactual_display_label():
    module = overpass_module()
    transport = httpx.MockTransport(lambda request: httpx.Response(
        200,
        json={"elements": [{
            "type": "node",
            "id": 20,
            "lat": 10.0001,
            "lon": 105.0,
            "tags": {"shop": "convenience"},
        }]},
        request=request,
    ))
    settings, _ = configured_settings(transport)

    result = asyncio.run(overpass_provider(module, settings).nearby(
        resolved(categories=("grocery",))
    ))

    assert result.status == "OK" and result.coverage == "PARTIAL"
    assert len(result.items) == 1
    assert result.items[0].provider_place_id == "node:20"
    assert result.items[0].name == "Unnamed OpenStreetMap place"


@pytest.mark.parametrize("element", [
    {
        "type": "node", "id": 31, "lat": 91, "lon": 105.0,
        "tags": {"shop": "supermarket", "name": "Synthetic"},
    },
    {
        "type": "way", "id": 32, "center": {"lat": 10.0},
        "tags": {"shop": "supermarket", "name": "Synthetic"},
    },
    {
        "type": "relation", "id": 33, "center": {"lat": 10.0, "lon": float("inf")},
        "tags": {"shop": "supermarket", "name": "Synthetic"},
    },
])
def test_node_way_and_relation_require_valid_coordinates(element):
    module = overpass_module()
    body = json.dumps({"elements": [element]}).encode("utf-8")
    transport = httpx.MockTransport(lambda request: httpx.Response(
        200, content=body, headers={"Content-Type": "application/json"}, request=request
    ))
    settings, _ = configured_settings(transport)

    result = asyncio.run(overpass_provider(module, settings).nearby(
        resolved(categories=("grocery",))
    ))

    assert result.status == "PROVIDER_ERROR"
    assert result.items == [] and result.coverage == "UNKNOWN" and not result.truncated
    assert result.evidence_kind == "SYNTHETIC_FIXTURE" and result.queried_at is not None


def test_disabled_settings_do_not_send_or_claim_empty():
    module = overpass_module()
    requests = []
    transport = httpx.MockTransport(
        lambda request: requests.append(request) or httpx.Response(
            200, json={"elements": []}, request=request
        )
    )
    settings, _ = configured_settings(transport, enabled=False)

    result = asyncio.run(overpass_provider(module, settings).nearby(
        resolved(categories=("grocery",))
    ))

    assert result.status == "NOT_CONFIGURED"
    assert result.evidence_kind == "NONE" and result.queried_at is None
    assert result.items == [] and result.coverage == "UNKNOWN" and not result.truncated
    assert requests == []


def test_adapter_instances_share_the_settings_gate_budget_and_reject_rebinding():
    module = overpass_module()
    requests = []
    transport = httpx.MockTransport(
        lambda request: requests.append(request) or httpx.Response(
            200, json={"elements": []}, request=request
        )
    )
    settings, gate = configured_settings(transport)
    first = overpass_provider(module, settings)
    second = overpass_provider(module, settings)

    first_result = asyncio.run(first.nearby(resolved(categories=("grocery",))))
    second_result = asyncio.run(second.nearby(resolved(categories=("grocery",))))

    assert settings.request_policy_gate is gate
    assert first._gate is second._gate is gate
    assert first_result.status == "EMPTY"
    assert second_result.status == "RATE_LIMITED"
    assert second_result.evidence_kind == "NONE" and second_result.queried_at is None
    assert second_result.items == [] and second_result.coverage == "UNKNOWN"
    assert len(requests) == 1
    with pytest.raises(ValueError, match="test seams are already bound"):
        module.OverpassPlacesProvider(settings, transport=httpx.MockTransport(
            lambda request: httpx.Response(200, json={"elements": []}, request=request)
        ))


def test_policy_failures_timeout_429_and_oversize_never_claim_empty():
    module = overpass_module()

    def observed(status, *, payload=None, content=None):
        requests = []
        transport = httpx.MockTransport(lambda request: requests.append(request) or httpx.Response(
            status,
            json=payload if content is None else None,
            content=content,
            request=request,
        ))
        settings, gate = configured_settings(transport)
        provider = overpass_provider(module, settings)
        result = asyncio.run(provider.nearby(resolved(categories=("grocery",))))
        assert settings.request_policy_gate is gate
        return result, requests

    rate_limited, rate_requests = observed(429, payload={"error": "synthetic"})
    provider_error, error_requests = observed(503, payload={"error": "synthetic"})
    oversized, oversized_requests = observed(200, content=b"x" * 1_048_577)

    timeout_clock = FakeClock()

    async def slow_resolver(host):
        assert host == "overpass.example.test"
        await timeout_clock.sleep(11.0)
        return ("93.184.216.34",)

    timeout_requests = []
    timeout_transport = httpx.MockTransport(
        lambda request: timeout_requests.append(request) or httpx.Response(
            200, json={"elements": []}, request=request
        )
    )
    timeout_settings, _ = configured_settings(
        timeout_transport, resolver=slow_resolver, clock=timeout_clock
    )
    timed_out = asyncio.run(overpass_provider(module, timeout_settings).nearby(
        resolved(categories=("grocery",))
    ))

    unapproved_requests = []
    unapproved_transport = httpx.MockTransport(
        lambda request: unapproved_requests.append(request) or httpx.Response(
            200, json={"elements": []}, request=request
        )
    )
    unapproved_settings, _ = configured_settings(
        unapproved_transport, include_policy=False
    )
    unapproved = asyncio.run(overpass_provider(module, unapproved_settings).nearby(
        resolved(categories=("grocery",))
    ))

    assert rate_limited.status == "RATE_LIMITED"
    assert provider_error.status == "PROVIDER_ERROR"
    assert oversized.status == "PROVIDER_ERROR"
    assert timed_out.status == "PROVIDER_ERROR"
    assert unapproved.status == "CAPABILITY_UNVERIFIED"
    for result in (rate_limited, provider_error):
        assert result.evidence_kind == "SYNTHETIC_FIXTURE" and result.queried_at is not None
    for result in (oversized, timed_out, unapproved):
        assert result.evidence_kind == "NONE" and result.queried_at is None
    for result in (rate_limited, provider_error, oversized, timed_out, unapproved):
        assert result.items == [] and result.coverage == "UNKNOWN" and not result.truncated
    assert len(rate_requests) == len(error_requests) == len(oversized_requests) == 1
    assert timeout_requests == [] and unapproved_requests == []


def test_private_overpass_failure_diagnostics_are_allowlisted_and_not_public(monkeypatch):
    module = overpass_module()

    def observed(status, *, payload=None, content=None, include_policy=True):
        transport = httpx.MockTransport(lambda request: httpx.Response(
            status,
            json=payload if content is None else None,
            content=content,
            request=request,
        ))
        settings, gate = configured_settings(transport, include_policy=include_policy)
        result = asyncio.run(overpass_provider(module, settings).nearby(
            resolved(categories=("grocery",))
        ))
        return result, gate

    non_200, non_200_gate = observed(503, payload={"error": "sentinel"})
    rate_limited, rate_gate = observed(429, payload={"error": "sentinel"})
    malformed, malformed_gate = observed(200, content=b"not-json")
    policy, policy_gate = observed(200, include_policy=False)
    empty, empty_gate = observed(200, payload={"elements": []})
    with monkeypatch.context() as seam:
        def invalid_query(request):
            raise ValueError("private query sentinel")
        seam.setattr(module, "build_overpass_query", invalid_query)
        invalid, invalid_gate = observed(200, payload={"elements": []})

    assert non_200.status == "PROVIDER_ERROR"
    assert rate_limited.status == "RATE_LIMITED"
    assert malformed.status == "PROVIDER_ERROR"
    assert invalid.status == "PROVIDER_ERROR"
    assert policy.status == "CAPABILITY_UNVERIFIED"
    assert empty.status == "EMPTY"
    assert non_200_gate.observation_stats()["provider_failures"] == {"osm_overpass": {"HTTP_NON_200": 1}}
    assert rate_gate.observation_stats()["provider_failures"] == {"osm_overpass": {"RATE_LIMITED": 1}}
    assert malformed_gate.observation_stats()["provider_failures"] == {"osm_overpass": {"MALFORMED_RESPONSE": 1}}
    assert policy_gate.observation_stats()["provider_failures"] == {"osm_overpass": {"POLICY_OR_TRANSPORT": 1}}
    assert invalid_gate.observation_stats()["provider_failures"] == {"osm_overpass": {"QUERY_INVALID": 1}}
    assert empty_gate.observation_stats()["provider_failures"] == {}
    assert invalid_gate.observation_stats()["backend_attempts"] == {}
    for result in (non_200, rate_limited, malformed, invalid, policy, empty):
        assert "provider_failures" not in result.model_dump()
        assert "sentinel" not in result.model_dump_json()
        assert not any(code in result.model_dump_json() for code in (
            "HTTP_NON_200", "MALFORMED_RESPONSE", "POLICY_OR_TRANSPORT", "QUERY_INVALID",
        ))
    non_200_stats = non_200_gate.observation_stats()
    non_200_stats["provider_failures"]["osm_overpass"]["HTTP_NON_200"] = 99
    assert non_200_gate.observation_stats()["provider_failures"] == {"osm_overpass": {"HTTP_NON_200": 1}}
    for provider_name, reason in (("arbitrary", "HTTP_NON_200"), ("osm_overpass", "private sentinel")):
        with pytest.raises(ValueError, match="Invalid provider failure code"):
            non_200_gate.record_provider_failure(provider_name, reason)
    assert non_200_gate.observation_stats()["provider_failures"] == {"osm_overpass": {"HTTP_NON_200": 1}}


@pytest.mark.parametrize("content", [
    b'{"remark":"private error","elements":[]}',
    b'{"osm3s":{"remark":"private partial"},"elements":[]}',
    b'{"version":0.6}',
    b'{"elements":[{"type":"node","id":1,"lat":91,"lon":105}]}',
])
def test_private_diagnostics_mark_all_malformed_responses_without_exposing_body(content):
    module = overpass_module()
    settings, gate = configured_settings(httpx.MockTransport(
        lambda request: httpx.Response(200, content=content, request=request)
    ))
    result = asyncio.run(overpass_provider(module, settings).nearby(resolved()))
    assert result.status == "PROVIDER_ERROR" and result.items == []
    assert gate.observation_stats()["provider_failures"] == {"osm_overpass": {"MALFORMED_RESPONSE": 1}}
    assert "private" not in result.model_dump_json()
    assert "private" not in repr(gate.observation_stats())


@pytest.mark.parametrize("scenario", ["oversize", "transport", "disabled", "cancelled"])
def test_private_diagnostics_keep_unobserved_errors_separate_from_disabled_or_cancelled(scenario):
    def respond(request):
        if scenario == "transport":
            raise httpx.ConnectError("private transport sentinel", request=request)
        if scenario == "cancelled":
            raise asyncio.CancelledError()
        return httpx.Response(200, content=b"x" * 1_048_577, request=request)
    settings, gate = configured_settings(httpx.MockTransport(respond), enabled=scenario != "disabled")
    provider = overpass_provider(overpass_module(), settings)
    if scenario == "cancelled":
        with pytest.raises(asyncio.CancelledError):
            asyncio.run(provider.nearby(resolved()))
    else:
        result = asyncio.run(provider.nearby(resolved()))
        assert result.status == ("NOT_CONFIGURED" if scenario == "disabled" else "PROVIDER_ERROR")
        assert result.evidence_kind == "NONE" and result.queried_at is None
        assert "private" not in result.model_dump_json()
    expected = {} if scenario in ("disabled", "cancelled") else {"osm_overpass": {"POLICY_OR_TRANSPORT": 1}}
    assert gate.observation_stats()["provider_failures"] == expected
