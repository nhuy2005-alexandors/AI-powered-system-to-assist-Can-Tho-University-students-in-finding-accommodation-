"""Offline contract checks for the bounded Nominatim-compatible adapter."""
import asyncio
from datetime import datetime, timedelta, timezone
import importlib
from pathlib import Path
from urllib.parse import parse_qs

import httpx
import pytest

from app.mobility.contracts import BoundingBox, GeocodeRequest


FIXTURES = Path(__file__).parent / "fixtures/open_mobility/geocoder"
BASE_URL = "https://nominatim.example.test"
SEARCH_PATH = "/search"
ATTRIBUTION = "Synthetic Nominatim attribution"


def nominatim_module():
    try:
        module = importlib.import_module("app.mobility.providers.nominatim_geocoder")
    except ModuleNotFoundError:
        module = None
    assert module is not None, "expected the owned Nominatim geocoder module to exist"
    return module


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
    assert host == "nominatim.example.test"
    return ("93.184.216.34",)


def configured_settings(
    transport,
    *,
    include_policy=True,
    enabled=True,
    live_enabled=True,
    geocoder_provider="nominatim",
    nominatim_url=BASE_URL,
    user_agent="NCKH synthetic geocoder fixture tests",
    max_requests=1,
    cache_policy="NO_CACHE_ALLOWED",
):
    from app.mobility.providers.network_policy import ProviderPolicy, policy_digest
    from app.mobility.providers.open_config import OpenMobilitySettings

    policy = ProviderPolicy(
        provider="nominatim",
        base_url=BASE_URL,
        allowed_paths=(SEARCH_PATH,),
        allowed_capabilities=("geocode",),
        attribution=(ATTRIBUTION,),
        user_agent=user_agent,
        cache_policy=cache_policy,
        policy_sha256="0" * 64,
        approved_until=datetime(2026, 10, 6, tzinfo=timezone.utc),
        max_requests=max_requests,
        max_rps=1.0,
        max_concurrency=1,
        timeout_seconds=10.0,
        connect_timeout_seconds=2.0,
        max_response_bytes=1_048_576,
    )
    digest = policy_digest(policy)
    policy = policy.model_copy(update={"policy_sha256": digest})
    settings = OpenMobilitySettings(
        _env_file=None,
        enabled=enabled,
        live_enabled=live_enabled,
        geocoder_provider=geocoder_provider,
        nominatim_url=nominatim_url,
        provider_policies={"nominatim": policy} if include_policy else {},
        expected_policy_hashes={"nominatim": digest} if include_policy else {},
    )
    settings.get_request_policy_gate(
        transport=transport,
        resolver=public_resolver,
        clock=FakeClock(),
    )
    return settings


def fixture_bytes(name):
    return (FIXTURES / name).read_bytes()


def default_request():
    return GeocodeRequest(
        address="Synthetic address",
        bounds=BoundingBox(south=9.9, west=105.5, north=10.2, east=105.9),
    )


@pytest.mark.parametrize("body,status", [(b'[]', "NO_MATCH"), (b'[{"lat":"10.01","lon":"105.77"}]', "OK"), (b'[{"lat":"10.01","lon":"105.77"},{"lat":"10.02","lon":"105.78"}]', "AMBIGUOUS")])
def test_cached_geocodes_coalesce_across_instances_and_return_copies(body, status):
    from app.mobility.providers.nominatim_geocoder import NominatimGeocoder
    sends = []
    transport = httpx.MockTransport(lambda req: sends.append(req) or httpx.Response(200, content=body))
    settings = configured_settings(transport, cache_policy="MEMORY_24H")
    a, b = NominatimGeocoder(settings), NominatimGeocoder(settings)
    async def run():
        first, second = await asyncio.gather(a.geocode(default_request()), b.geocode(default_request()))
        assert first.status == second.status == status
        first.attribution.clear()
        if first.position:
            first.position.lat = 0
        third = await b.geocode(default_request())
        assert third.attribution == [ATTRIBUTION]
        assert third.queried_at == second.queried_at
        if third.position:
            assert third.position.lat == 10.01
    asyncio.run(run())
    assert len(sends) == 1


def test_cache_distinguishes_bounds_expires_and_does_not_cache_errors():
    from app.mobility.providers.nominatim_geocoder import NominatimGeocoder
    codes = [429, 200, 200, 200]
    sends = []
    def respond(req):
        sends.append(req)
        return httpx.Response(codes.pop(0), content=b'[]')
    transport = httpx.MockTransport(respond)
    settings = configured_settings(transport, cache_policy="MEMORY_24H", max_requests=4)
    gate = settings.request_policy_gate
    provider = NominatimGeocoder(settings)
    async def run():
        assert (await provider.geocode(default_request())).status == "RATE_LIMITED"
        assert (await provider.geocode(default_request())).status == "NO_MATCH"
        other = default_request().model_copy(update={"bounds": BoundingBox(south=9.95,west=105.5,north=10.2,east=105.9)})
        assert (await provider.geocode(other)).status == "NO_MATCH"
        gate._clock.now += timedelta(hours=24)
        gate._clock.elapsed += 86400
        # Keep approval valid while the result TTL expires.
        assert (await provider.geocode(default_request())).status == "NO_MATCH"
    # Original synthetic expiry is Oct 6 at midnight; use a shorter start for TTL test.
    gate._clock.now = datetime(2026, 10, 4, 12, tzinfo=timezone.utc)
    asyncio.run(run())
    assert len(sends) == 4


@pytest.mark.parametrize("mutation", ["expired", "disabled", "hash"])
def test_cache_never_bypasses_revocation_or_expiry(mutation):
    from app.mobility.providers.nominatim_geocoder import NominatimGeocoder
    sends = []
    transport = httpx.MockTransport(lambda req: sends.append(req) or httpx.Response(200, content=b'[]'))
    settings = configured_settings(transport, cache_policy="MEMORY_24H")
    provider = NominatimGeocoder(settings)
    gate = settings.request_policy_gate
    async def run():
        assert (await provider.geocode(default_request())).status == "NO_MATCH"
        if mutation == "expired":
            gate._clock.now += timedelta(days=2)
        elif mutation == "disabled":
            gate._live_enabled = False
        else:
            gate._expected_hashes = {"nominatim": "0" * 64}
        assert (await provider.geocode(default_request())).status in {"NOT_CONFIGURED", "CAPABILITY_UNVERIFIED"}
    asyncio.run(run())
    assert len(sends) == 1


def test_cache_lru_is_bounded_to_128_and_old_entry_is_refetched():
    from app.mobility.providers.nominatim_geocoder import NominatimGeocoder
    sends = []
    transport = httpx.MockTransport(lambda req: sends.append(req) or httpx.Response(200, content=b'[]'))
    settings = configured_settings(transport, cache_policy="MEMORY_24H", max_requests=131)
    provider = NominatimGeocoder(settings)
    async def run():
        for i in range(129):
            assert (await provider.geocode(default_request().model_copy(update={"address": f"Synthetic place {i}"}))).status == "NO_MATCH"
        await provider.geocode(default_request().model_copy(update={"address": "Synthetic place 0"}))
    asyncio.run(run())
    assert len(sends) == 130


def test_cache_canonicalization_and_hit_never_resolves_dns():
    from app.mobility.providers.nominatim_geocoder import NominatimGeocoder
    sends = []
    transport = httpx.MockTransport(lambda req: sends.append(req) or httpx.Response(200, content=b'[]'))
    settings = configured_settings(transport, cache_policy="MEMORY_24H")
    provider = NominatimGeocoder(settings)
    async def run():
        first = default_request().model_copy(update={"address": "  Cafe\u0301   public\tplace  "})
        assert (await provider.geocode(first)).status == "NO_MATCH"
        async def forbidden_dns(_host):
            raise AssertionError("cache hit must not resolve DNS")
        settings.request_policy_gate._resolver = forbidden_dns
        second = default_request().model_copy(update={"address": "Café public place"})
        assert (await provider.geocode(second)).status == "NO_MATCH"
        assert settings.request_policy_gate.observation_stats()["cache_hits"] == 1
    asyncio.run(run())
    assert len(sends) == 1
    assert sends[0].url.params["q"] == "Café public place"


def test_cancelled_geocode_releases_shared_cache_lock():
    from app.mobility.providers.nominatim_geocoder import NominatimGeocoder
    async def run():
        entered = asyncio.Event()
        blocked = asyncio.Event()
        calls = []
        async def respond(req):
            calls.append(req)
            if len(calls) == 1:
                entered.set()
                await blocked.wait()
            return httpx.Response(200, content=b'[]')
        transport = httpx.MockTransport(respond)
        settings = configured_settings(transport, cache_policy="MEMORY_24H", max_requests=2)
        provider = NominatimGeocoder(settings)
        first = asyncio.create_task(provider.geocode(default_request()))
        await asyncio.wait_for(entered.wait(), timeout=1)
        first.cancel()
        with pytest.raises(asyncio.CancelledError):
            await first
        result = await asyncio.wait_for(provider.geocode(default_request()), timeout=1)
        assert result.status == "NO_MATCH"
        assert len(calls) == 2
        assert settings.request_policy_gate.observation_stats()["cache_entries"] == 1
    asyncio.run(run())


def geocode_fixture(name):
    return geocode_body(fixture_bytes(name))


def geocode_body(body, *, status_code=200, request=None, settings_options=None):
    requests = []
    def respond(sent):
        requests.append(sent)
        return httpx.Response(status_code, content=body, request=sent)

    transport = httpx.MockTransport(respond)
    settings = configured_settings(transport, **(settings_options or {}))
    provider_type = getattr(nominatim_module(), "NominatimGeocoder", None)
    assert provider_type is not None, "NominatimGeocoder is not implemented"
    provider = provider_type(settings, transport=transport)
    result = asyncio.run(provider.geocode(request or default_request()))
    return result, requests


def test_empty_response_uses_bounded_search_and_returns_no_match():
    fixture = fixture_bytes("empty.json")
    requests = []

    def respond(request):
        requests.append(request)
        return httpx.Response(200, content=fixture, request=request)

    transport = httpx.MockTransport(respond)
    settings = configured_settings(transport)
    provider_type = getattr(nominatim_module(), "NominatimGeocoder", None)
    assert provider_type is not None, "NominatimGeocoder is not implemented"
    provider = provider_type(settings, transport=transport)
    request = GeocodeRequest(
        address="  Synthetic address  ",
        bounds=BoundingBox(south=9.9, west=105.5, north=10.2, east=105.9),
    )

    result = asyncio.run(provider.geocode(request))

    assert len(requests) == 1
    sent = requests[0]
    assert sent.method == "GET"
    assert sent.url.path == SEARCH_PATH
    params = parse_qs(sent.url.query.decode("ascii"))
    assert params == {
        "format": ["jsonv2"],
        "limit": ["5"],
        "bounded": ["1"],
        "q": ["Synthetic address"],
        "viewbox": ["105.5,10.2,105.9,9.9"],
    }
    assert result.provider == "nominatim"
    assert result.status == "NO_MATCH"
    assert result.candidate_count == 0
    assert result.position is None
    assert result.queried_at is not None
    assert result.evidence_kind == "SYNTHETIC_FIXTURE"
    assert result.attribution == [ATTRIBUTION]


def test_single_candidate_is_approximate_and_does_not_copy_provider_identity():
    result, requests = geocode_fixture("single.json")

    assert len(requests) == 1
    assert result.status == "OK"
    assert result.candidate_count == 1
    assert result.position is not None
    assert result.position.lat == 10.01
    assert result.position.lng == 105.77
    assert result.position.precision == "APPROXIMATE"
    assert result.position.source == "nominatim"
    assert result.position.verified_at is None
    assert "synthetic fixture label only" not in result.model_dump_json()
    assert result.evidence_kind == "SYNTHETIC_FIXTURE"
    assert result.queried_at is not None


def test_multiple_candidates_are_ambiguous_without_selecting_the_first():
    result, requests = geocode_fixture("multiple.json")

    assert len(requests) == 1
    assert result.status == "AMBIGUOUS"
    assert result.candidate_count == 3
    assert result.position is None
    assert result.evidence_kind == "SYNTHETIC_FIXTURE"
    assert result.queried_at is not None


def test_request_bounds_outside_static_ceiling_are_unobserved_and_never_sent():
    request = GeocodeRequest(
        address="Synthetic address",
        bounds=BoundingBox(south=9.9, west=105.5, north=10.31, east=105.9),
    )
    result, requests = geocode_body(b"[]", request=request)

    assert requests == []
    assert result.status == "UNSUPPORTED_REGION"
    assert result.candidate_count == 0
    assert result.position is None
    assert result.queried_at is None
    assert result.evidence_kind == "NONE"


@pytest.mark.parametrize(
    "settings_options",
    [
        {"enabled": False},
        {"live_enabled": False},
        {"geocoder_provider": "disabled"},
        {"nominatim_url": ""},
    ],
)
def test_disabled_or_missing_endpoint_is_not_configured_without_send(settings_options):
    result, requests = geocode_body(b"[]", settings_options=settings_options)

    assert requests == []
    assert result.status == "NOT_CONFIGURED"
    assert result.candidate_count == 0
    assert result.position is None
    assert result.queried_at is None
    assert result.evidence_kind == "NONE"


@pytest.mark.parametrize(
    "settings_options",
    [
        {"include_policy": False},
        {"user_agent": None},
    ],
)
def test_missing_policy_or_identifying_user_agent_is_unverified_without_send(settings_options):
    result, requests = geocode_body(b"[]", settings_options=settings_options)

    assert requests == []
    assert result.status == "CAPABILITY_UNVERIFIED"
    assert result.candidate_count == 0
    assert result.position is None
    assert result.queried_at is None
    assert result.evidence_kind == "NONE"


@pytest.mark.parametrize(
    "status_code,expected_status,observed",
    [
        (429, "RATE_LIMITED", True),
        (500, "PROVIDER_ERROR", True),
        (206, "PROVIDER_ERROR", True),
        (302, "PROVIDER_ERROR", False),
    ],
)
def test_non_success_http_status_preserves_only_returned_provider_observation(
    status_code, expected_status, observed,
):
    result, requests = geocode_body(b"[]", status_code=status_code)

    assert len(requests) == 1
    assert result.status == expected_status
    assert result.candidate_count == 0
    assert result.position is None
    assert (result.queried_at is not None) is observed
    assert result.evidence_kind == ("SYNTHETIC_FIXTURE" if observed else "NONE")
    assert result.attribution == ([ATTRIBUTION] if observed else [])


def test_policy_budget_is_shared_across_geocoder_instances_and_failures_are_unobserved():
    requests = []
    transport = httpx.MockTransport(
        lambda sent: requests.append(sent) or httpx.Response(200, content=b"[]", request=sent)
    )
    settings = configured_settings(transport, max_requests=1)
    provider_type = getattr(nominatim_module(), "NominatimGeocoder", None)
    assert provider_type is not None, "NominatimGeocoder is not implemented"
    first_provider = provider_type(settings, transport=transport)
    second_provider = provider_type(settings, transport=transport)

    async def query_twice():
        first = await first_provider.geocode(default_request())
        second = await second_provider.geocode(default_request())
        return first, second

    first, second = asyncio.run(query_twice())

    assert first.status == "NO_MATCH"
    assert first.evidence_kind == "SYNTHETIC_FIXTURE"
    assert second.status == "RATE_LIMITED"
    assert second.candidate_count == 0
    assert second.position is None
    assert second.queried_at is None
    assert second.evidence_kind == "NONE"
    assert requests and len(requests) == 1


def test_transport_failure_is_unobserved_and_does_not_expose_error_text():
    requests = []

    def fail(sent):
        requests.append(sent)
        raise httpx.ConnectError("synthetic private transport detail", request=sent)

    transport = httpx.MockTransport(fail)
    settings = configured_settings(transport)
    provider_type = getattr(nominatim_module(), "NominatimGeocoder", None)
    assert provider_type is not None, "NominatimGeocoder is not implemented"
    provider = provider_type(settings, transport=transport)

    result = asyncio.run(provider.geocode(default_request()))

    assert len(requests) == 1
    assert result.status == "PROVIDER_ERROR"
    assert result.candidate_count == 0
    assert result.position is None
    assert result.queried_at is None
    assert result.evidence_kind == "NONE"
    assert "synthetic private transport detail" not in repr(result)


@pytest.mark.parametrize(
    "body",
    [
        b"not json",
        b"{}",
        b"[null]",
        b"[{}]",
        b'[{"lat":"NaN","lon":"105.77"}]',
        b'[{"lat":"10.01","lon":"Infinity"}]',
        b'[{"lat":"90.1","lon":"105.77"}]',
        b'[{"lat":10.01,"lon":"105.77"}]',
        b'[{"lat":"10.01","lon":"105.77"},{"lat":"10.21","lon":"105.78"}]',
    ],
)
def test_malformed_or_out_of_bounds_candidate_fails_the_whole_response(body):
    result, requests = geocode_body(body)

    assert len(requests) == 1
    assert result.status == "PROVIDER_ERROR"
    assert result.candidate_count == 0
    assert result.position is None
    assert result.queried_at is not None
    assert result.evidence_kind == "SYNTHETIC_FIXTURE"
    assert result.attribution == [ATTRIBUTION]


def test_response_with_more_than_five_candidates_is_malformed():
    candidate = b'{"lat":"10.01","lon":"105.77"}'
    body = b"[" + b",".join([candidate] * 6) + b"]"
    result, requests = geocode_body(body)

    assert len(requests) == 1
    assert result.status == "PROVIDER_ERROR"
    assert result.candidate_count == 0
    assert result.position is None
    assert result.evidence_kind == "SYNTHETIC_FIXTURE"


def test_duplicate_json_coordinate_key_is_malformed_not_cherry_picked():
    result, requests = geocode_body(
        b'[{"lat":"10.01","lon":"105.77","lat":"10.02"}]'
    )

    assert len(requests) == 1
    assert result.status == "PROVIDER_ERROR"
    assert result.candidate_count == 0
    assert result.position is None
    assert result.evidence_kind == "SYNTHETIC_FIXTURE"
    assert result.queried_at is not None


def test_candidate_just_outside_request_bound_is_not_rounded_inside():
    result, requests = geocode_body(
        b'[{"lat":"10.20000000000000000001","lon":"105.77"}]'
    )

    assert len(requests) == 1
    assert result.status == "PROVIDER_ERROR"
    assert result.candidate_count == 0
    assert result.position is None


def test_deeply_nested_and_huge_coordinate_payloads_fail_closed():
    deeply_nested = b"[" * 2000 + b"0" + b"]" * 2000
    huge_coordinate = b'[{"lat":"' + b"9" * 10000 + b'","lon":"105.77"}]'

    nested_result, nested_requests = geocode_body(deeply_nested)
    huge_result, huge_requests = geocode_body(huge_coordinate)

    assert len(nested_requests) == len(huge_requests) == 1
    for result in (nested_result, huge_result):
        assert result.status == "PROVIDER_ERROR"
        assert result.candidate_count == 0
        assert result.position is None
        assert result.evidence_kind == "SYNTHETIC_FIXTURE"
        assert result.queried_at is not None


def test_nonstandard_json_constant_makes_the_response_malformed():
    result, requests = geocode_body(
        b'[{"lat":"10.01","lon":"105.77","metadata":NaN}]'
    )

    assert len(requests) == 1
    assert result.status == "PROVIDER_ERROR"
    assert result.candidate_count == 0
    assert result.position is None
    assert result.evidence_kind == "SYNTHETIC_FIXTURE"
    assert result.queried_at is not None


def test_response_over_policy_size_limit_fails_without_observed_payload():
    result, requests = geocode_body(b" " * 1_048_577)

    assert len(requests) == 1
    assert result.status == "PROVIDER_ERROR"
    assert result.candidate_count == 0
    assert result.position is None
    assert result.evidence_kind == "NONE"
    assert result.queried_at is None
    module = nominatim_module()
    assert getattr(module, "NominatimGeocoder", None) is not None, (
        "expected NominatimGeocoder in the owned adapter module"
    )
