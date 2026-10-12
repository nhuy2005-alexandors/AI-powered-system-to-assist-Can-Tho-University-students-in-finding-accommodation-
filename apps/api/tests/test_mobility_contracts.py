"""Contracts reject unsafe coordinates, ambiguous time and false success payloads."""
from datetime import datetime, timezone
import importlib
import json
from pathlib import Path
import subprocess

import pytest
from pydantic import ValidationError


def contracts():
    # Missing feature must be a causal RED assertion, not a collection failure.
    try:
        return importlib.import_module("app.mobility.contracts")
    except ModuleNotFoundError:
        pytest.fail("mobility wire contracts are not implemented")


@pytest.mark.parametrize("lat,lng", [(91, 105), (10, 181), (float("nan"), 105), (10, float("inf"))])
def test_position_rejects_unusable_coordinates(lat, lng):
    c = contracts()
    with pytest.raises(ValidationError):
        c.Position(lat=lat, lng=lng)


def test_position_preserves_unknown_precision_and_nullable_evidence():
    c = contracts()
    p = c.Position(lat=10.03, lng=105.76)
    assert p.model_dump(mode="json") == {
        "lat": 10.03, "lng": 105.76, "precision": "UNKNOWN", "source": None,
        "verified_at": None,
    }


def test_bus_requires_offset_aware_departure_time():
    c = contracts()
    for value in (None, "2026-10-04T08:00:00"):
        with pytest.raises(ValidationError):
            c.RouteRequest(listing_id=1, campus_id="khu_ii", requested_mode="BUS", departure_time=value)
    r = c.RouteRequest(listing_id=1, campus_id="khu_ii", requested_mode="BUS",
                       departure_time="2026-10-04T08:00:00+07:00")
    assert r.departure_time.utcoffset().total_seconds() == 25200
    assert r.direction == "LISTING_TO_CAMPUS"


@pytest.mark.parametrize("extra", [
    {"requested_mode": "DRIVE"}, {"campus_id": "untrusted"},
    {"origin_url": "https://example.test"}, {"listing_id": 0},
    {"direction": "CAMPUS_TO_LISTING"},
])
def test_route_rejects_fallback_mode_unknown_campus_extra_fields_and_direction(extra):
    c = contracts()
    params = {"listing_id": 1, "campus_id": "khu_i", "requested_mode": "MOTORBIKE"}
    with pytest.raises(ValidationError):
        c.RouteRequest(**(params | extra))


def test_bbox_rejects_reversed_extents():
    c = contracts()
    with pytest.raises(ValidationError):
        c.BoundingBox(south=11, north=10, west=105, east=106)
    with pytest.raises(ValidationError):
        c.BoundingBox(south=10, north=11, west=106, east=105)


@pytest.mark.parametrize("radius", [0, -1, 750, float("nan")])
def test_nearby_rejects_non_product_radius(radius):
    c = contracts()
    with pytest.raises(ValidationError):
        c.NearbyRequest(listing_id=1, radius_m=radius)


def test_nearby_categories_are_explicit_and_unique():
    c = contracts()
    for categories in ([], ["phone"], ["police", "police"]):
        with pytest.raises(ValidationError):
            c.NearbyRequest(listing_id=1, categories=categories)
    assert c.NearbyRequest(listing_id=1).radius_m == 1000


def test_catalog_does_not_convert_unknown_area_or_flags_to_false():
    c = contracts()
    listing = c.CatalogListing(id=1, title="Synthetic housing", source="chotot", source_id="123")
    assert listing.area is None
    assert listing.position is None
    assert listing.description_is_partial is None
    assert listing.unit_type_uncertain is None
    assert "source_record" not in listing.model_dump()


def test_failed_route_cannot_report_zero_as_success():
    c = contracts()
    payload = dict(listing_id=1, campus_id="khu_ii", requested_mode="WALK",
                   status="NO_ROUTE", coordinate_version="v1")
    r = c.RouteResult(**payload)
    assert r.duration_seconds is None and r.distance_meters is None
    with pytest.raises(ValidationError):
        c.RouteResult(**payload, duration_seconds=0)
    with pytest.raises(ValidationError):
        c.RouteResult(**(payload | {"status": "OK"}))


def test_fixture_route_success_carries_matching_mode_and_evidence():
    c = contracts()
    r = c.RouteResult(listing_id=1, campus_id="khu_ii", requested_mode="WALK",
                      effective_mode="WALK", status="OK", duration_seconds=90,
                      distance_meters=100, coordinate_version="v1",
                      observed_at=datetime(2026, 10, 4, tzinfo=timezone.utc),
                      evidence_kind="SYNTHETIC_FIXTURE")
    assert r.model_dump(mode="json")["evidence_kind"] == "SYNTHETIC_FIXTURE"
    with pytest.raises(ValidationError):
        c.RouteResult(**(r.model_dump() | {"effective_mode": "MOTORBIKE"}))


def test_new_route_and_nearby_results_default_to_neutral_provider_metadata():
    c = contracts()
    route = c.RouteResult(
        listing_id=1, campus_id="khu_ii", requested_mode="WALK",
        status="NOT_CONFIGURED", coordinate_version="v1",
    )
    nearby = c.NearbyResult(
        listing_id=1, radius_m=1000, categories=["police"], status="NOT_CONFIGURED",
    )
    measured = c.RouteResult(
        listing_id=1, campus_id="khu_ii", provider="ors", requested_mode="WALK",
        effective_mode="WALK", status="OK", duration_seconds=240,
        distance_meters=510, coordinate_version="v1", evidence_kind="SYNTHETIC_FIXTURE",
        attribution=["Synthetic ORS fixture"], provider_profile="foot-walking",
    )

    assert route.provider == "none"
    assert route.attribution == [] and route.provider_profile is None
    assert nearby.provider == "none"
    assert measured.provider == "ors"
    assert measured.attribution == ["Synthetic ORS fixture"]
    assert measured.provider_profile == "foot-walking"


def test_geocoder_contract_strips_address_and_never_accepts_ambiguous_position():
    c = contracts()
    try:
        request_type = c.GeocodeRequest
        result_type = c.GeocodeResult
    except AttributeError as exc:
        pytest.fail(f"open geocoder contract is not implemented: {exc}")

    bounds = c.BoundingBox(south=10, north=11, west=105, east=106)
    request = request_type(address="  12 Nguyen Van Linh  ", bounds=bounds)
    assert request.address == "12 Nguyen Van Linh"

    position = c.Position(lat=10.03, lng=105.76, precision="APPROXIMATE", source="nominatim")
    result = result_type(
        provider="nominatim", status="OK", position=position, candidate_count=1,
        queried_at="2026-10-05T01:00:00Z", evidence_kind="SYNTHETIC_FIXTURE",
        attribution=["Synthetic geocoder fixture"],
    )
    assert result.position.precision == "APPROXIMATE"
    with pytest.raises(ValidationError):
        request_type(address="   ", bounds=bounds)
    with pytest.raises(ValidationError):
        result_type(
            provider="nominatim", status="AMBIGUOUS", position=position, candidate_count=2,
            queried_at="2026-10-05T01:00:00Z", evidence_kind="SYNTHETIC_FIXTURE",
            attribution=["Synthetic geocoder fixture"],
        )
    with pytest.raises(ValidationError):
        result_type(
            provider="nominatim", status="OK", position=None, candidate_count=1,
            queried_at="2026-10-05T01:00:00Z", evidence_kind="SYNTHETIC_FIXTURE",
            attribution=["Synthetic geocoder fixture"],
        )


def test_geocoder_preflight_statuses_are_strictly_unobserved():
    c = contracts()
    for status in ("NOT_CONFIGURED", "CAPABILITY_UNVERIFIED", "UNSUPPORTED_REGION"):
        result = c.GeocodeResult(
            provider="nominatim",
            status=status,
            position=None,
            candidate_count=0,
            queried_at=None,
            evidence_kind="NONE",
        )
        assert result.status == status
        assert result.position is None and result.candidate_count == 0
        assert result.queried_at is None and result.evidence_kind == "NONE"

    for status in ("NOT_CONFIGURED", "CAPABILITY_UNVERIFIED", "UNSUPPORTED_REGION"):
        for invalid in (
            {"evidence_kind": "LIVE"},
            {"queried_at": "2026-10-05T01:00:00Z"},
            {"candidate_count": 1},
            {"position": c.Position(lat=10.03, lng=105.76, precision="APPROXIMATE")},
        ):
            with pytest.raises(ValidationError):
                c.GeocodeResult(**({
                    "provider": "nominatim",
                    "status": status,
                    "position": None,
                    "candidate_count": 0,
                    "queried_at": None,
                    "evidence_kind": "NONE",
                } | invalid))


@pytest.mark.parametrize(
    "status,count,has_position",
    [("OK", 1, True), ("NO_MATCH", 0, False), ("AMBIGUOUS", 2, False)],
)
def test_geocoder_observed_results_require_time_evidence_and_exact_candidate_count(
    status, count, has_position,
):
    c = contracts()
    position = (
        c.Position(lat=10.03, lng=105.76, precision="APPROXIMATE", source="nominatim")
        if has_position else None
    )
    for evidence in ("SYNTHETIC_FIXTURE", "LIVE"):
        result = c.GeocodeResult(
            provider="nominatim",
            status=status,
            position=position,
            candidate_count=count,
            queried_at="2026-10-05T01:00:00Z",
            evidence_kind=evidence,
        )
        assert result.candidate_count == count
        assert result.evidence_kind == evidence
        assert result.queried_at.utcoffset().total_seconds() == 0
    wrong_candidate_count = 1 if status == "AMBIGUOUS" else count + 1
    for invalid in (
        {"queried_at": None},
        {"evidence_kind": "NONE"},
        {"candidate_count": wrong_candidate_count},
    ):
        with pytest.raises(ValidationError):
            c.GeocodeResult(**({
                "provider": "nominatim",
                "status": status,
                "position": position,
                "candidate_count": count,
                "queried_at": "2026-10-05T01:00:00Z",
                "evidence_kind": "SYNTHETIC_FIXTURE",
            } | invalid))


@pytest.mark.parametrize("status", ["RATE_LIMITED", "PROVIDER_ERROR"])
def test_geocoder_errors_allow_only_paired_local_or_observed_metadata(status):
    c = contracts()
    local = c.GeocodeResult(
        provider="nominatim",
        status=status,
        candidate_count=0,
        evidence_kind="NONE",
    )
    observed = c.GeocodeResult(
        provider="nominatim",
        status=status,
        candidate_count=0,
        queried_at="2026-10-05T01:00:00Z",
        evidence_kind="SYNTHETIC_FIXTURE",
    )
    assert local.queried_at is None and local.evidence_kind == "NONE"
    assert observed.queried_at is not None and observed.evidence_kind == "SYNTHETIC_FIXTURE"
    for invalid in (
        {"queried_at": "2026-10-05T01:00:00Z", "evidence_kind": "NONE"},
        {"queried_at": None, "evidence_kind": "LIVE"},
        {"candidate_count": 1},
        {"position": c.Position(lat=10.03, lng=105.76, precision="APPROXIMATE")},
    ):
        with pytest.raises(ValidationError):
            c.GeocodeResult(**({
                "provider": "nominatim",
                "status": status,
                "position": None,
                "candidate_count": 0,
                "queried_at": None,
                "evidence_kind": "NONE",
            } | invalid))


def test_nearby_empty_is_distinct_from_disabled():
    c = contracts()
    kwargs = dict(listing_id=1, radius_m=1000, categories=["police"])
    result = c.NearbyResult(**kwargs, status="EMPTY", evidence_kind="SYNTHETIC_FIXTURE",
                            queried_at=datetime(2026, 10, 4, tzinfo=timezone.utc), coverage="PARTIAL")
    assert result.status == "EMPTY"
    disabled = c.NearbyResult(**kwargs, status="NOT_CONFIGURED")
    assert disabled.evidence_kind == "NONE" and disabled.coverage == "UNKNOWN"


def test_campuses_use_one_provisional_registry():
    contracts()
    module = importlib.import_module("app.mobility.campuses")
    assert [c.id for c in module.CAMPUSES] == ["khu_i", "khu_ii", "khu_iii"]
    assert [(c.lat, c.lng) for c in module.CAMPUSES] == [
        (10.0159, 105.7656), (10.0322, 105.7683), (10.0340, 105.7798),
    ]
    assert all(c.verification_status == "PROVISIONAL" for c in module.CAMPUSES)


def test_provider_base_blocks_live_network_and_hides_secret():
    contracts()
    base = importlib.import_module("app.mobility.providers.base")
    config = base.MobilitySettings(server_api_key="sentinel-secret")
    assert "sentinel-secret" not in repr(config)
    assert base.request_gate(config, "WALK", None) == "NOT_CONFIGURED"
    enabled = base.MobilitySettings(enabled=True, live_enabled=True, server_api_key="sentinel-secret",
                                    allowed_modes={"WALK"})
    # This phase never enables real HTTP even if flags/key are supplied accidentally.
    assert base.request_gate(enabled, "WALK", None) == "CAPABILITY_UNVERIFIED"


def test_bus_wire_time_rejects_numeric_and_non_rfc3339():
    c = contracts()
    for value in (1700000000, "2026-10-04 08:00:00+07:00"):
        with pytest.raises(ValidationError):
            c.RouteRequest(listing_id=1, campus_id="khu_ii", requested_mode="BUS", departure_time=value)


def test_verified_position_requires_source_and_aware_evidence():
    c = contracts()
    for extra in ({}, {"source": "survey", "verified_at": "2026-10-04T08:00:00"}):
        with pytest.raises(ValidationError):
            c.Position(lat=10, lng=105, precision="VERIFIED", **extra)
    p = c.Position(lat=10, lng=105, precision="VERIFIED", source="survey",
                   verified_at="2026-10-04T08:00:00+07:00")
    assert p.verified_at.isoformat() == "2026-10-04T01:00:00+00:00"


@pytest.mark.parametrize("kind", ["route", "nearby", "warning"])
def test_returned_timestamps_reject_naive_values(kind):
    c = contracts()
    with pytest.raises(ValidationError):
        if kind == "route":
            c.RouteResult(listing_id=1, campus_id="khu_i", requested_mode="WALK",
                          status="NOT_CONFIGURED", coordinate_version="v1",
                          observed_at="2026-10-04T08:00:00")
        elif kind == "nearby":
            c.NearbyResult(listing_id=1, radius_m=1000, categories=["police"],
                           status="PROVIDER_ERROR", queried_at="2026-10-04T08:00:00")
        else:
            c.LocationWarning(code="TEST", severity="INFO", message="Synthetic", scope="test",
                              evidence_source="test", observed_at="2026-10-04T08:00:00")


@pytest.mark.parametrize("status", ["NOT_CONFIGURED", "PROVIDER_ERROR"])
def test_nearby_error_cannot_claim_partial_coverage(status):
    c = contracts()
    with pytest.raises(ValidationError):
        c.NearbyResult(listing_id=1, radius_m=1000, categories=["police"], status=status,
                       evidence_kind="LIVE", coverage="PARTIAL")


def test_disabled_nearby_cannot_claim_live_observation():
    c = contracts()
    with pytest.raises(ValidationError):
        c.NearbyResult(listing_id=1, radius_m=1000, categories=["police"],
                       status="NOT_CONFIGURED", evidence_kind="LIVE")


def test_shared_wire_fixture_checked_by_python_and_typescript():
    c = contracts()
    fixture = Path(__file__).parent / "fixtures/mobility/contracts.json"
    assert fixture.exists(), "shared Python/TypeScript wire fixture missing"
    payload = json.loads(fixture.read_text(encoding="utf-8"))
    for model in ("CatalogListing", "CatalogPage", "Campus", "RouteRequest", "RouteResult",
                  "NearbyRequest", "NearbyResult", "LocationWarning", "Place"):
        getattr(c, model).model_validate(payload[model])
    root = Path(__file__).resolve().parents[3]
    result = subprocess.run(["node", str(root / "apps/web/e2e/verify-mobility-contract.cjs"), str(fixture)],
                            capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stdout + result.stderr


def test_app_settings_keep_google_server_key_secret_and_feature_disabled():
    from app.config import Settings
    config = Settings(_env_file=None, mobility_enabled=False, google_live_enabled=False,
                      google_server_api_key="sentinel-google-key")
    assert config.mobility_enabled is False
    assert config.google_live_enabled is False
    assert "sentinel-google-key" not in repr(config)
