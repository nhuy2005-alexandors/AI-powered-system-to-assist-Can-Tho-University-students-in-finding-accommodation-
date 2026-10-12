"""Evidence-based location and route warnings."""
import importlib

import pytest

from app.mobility.contracts import (
    CatalogListing,
    Position,
    RouteResult,
)


def warnings_module():
    try:
        return importlib.import_module("app.mobility.warnings")
    except ModuleNotFoundError as exc:
        pytest.fail(f"mobility warnings are not implemented: {exc.name}")


def listing(**overrides):
    values = {
        "id": 3,
        "title": "Synthetic student room",
        "source": "fixture",
        "source_id": "room-3",
        "description_state": "PARTIAL",
        "description_is_partial": True,
        "unit_type_uncertain": None,
        "lease_transfer_terms_verified": None,
        "parsed_amenities": None,
        "position": Position(lat=10.01, lng=105.77, precision="APPROXIMATE", source="fixture"),
    }
    values.update(overrides)
    return CatalogListing(**values)


def route(*, mode="WALK", status="OK", evidence="SYNTHETIC_FIXTURE", provider="google"):
    return RouteResult(
        listing_id=3,
        campus_id="khu_ii",
        provider=provider,
        requested_mode=mode,
        effective_mode=mode if status == "OK" else None,
        status=status,
        duration_seconds=300 if status == "OK" else None,
        distance_meters=600 if status == "OK" else None,
        coordinate_version="legacy-2026-07-06-provisional",
        evidence_kind=evidence,
    )


def codes(warnings):
    return {warning.code for warning in warnings}


def test_warnings_preserve_approximate_location_partial_description_and_unknown_flags():
    warnings = warnings_module().build_warnings(listing(), None)

    assert {
        "APPROXIMATE_LOCATION",
        "ROUTE_NOT_VERIFIED",
        "PARTIAL_DESCRIPTION",
        "UNIT_TYPE_UNKNOWN",
        "TRANSFER_TERMS_UNVERIFIED",
    } <= codes(warnings)
    by_code = {warning.code: warning for warning in warnings}
    assert by_code["APPROXIMATE_LOCATION"].severity == "CAUTION"
    assert by_code["APPROXIMATE_LOCATION"].scope == "listing"
    assert by_code["UNIT_TYPE_UNKNOWN"].severity == "CAUTION"
    assert all(warning.observed_at is None for warning in warnings)


def test_clear_rental_with_unknown_transfer_flag_is_not_labeled_transfer_uncertain():
    warnings = warnings_module().build_warnings(
        listing(offer_kind="rental", offer_context_uncertain=False,
                lease_transfer_terms_verified=None),
        None,
    )

    assert "TRANSFER_TERMS_UNVERIFIED" not in codes(warnings)


@pytest.mark.parametrize(("offer_kind", "offer_context_uncertain", "expected_warning"), [
    ("lease_transfer", False, True),
    ("unknown", False, True),
    (None, False, True),
    ("rental", True, True),
    ("rental", None, False),
    ("rental", False, False),
])
def test_transfer_warning_requires_transfer_or_explicitly_uncertain_offer_context(
        offer_kind, offer_context_uncertain, expected_warning):
    warnings = warnings_module().build_warnings(
        listing(offer_kind=offer_kind, offer_context_uncertain=offer_context_uncertain,
                lease_transfer_terms_verified=None),
        None,
    )

    assert ("TRANSFER_TERMS_UNVERIFIED" in codes(warnings)) is expected_warning


def test_missing_or_unverified_position_is_not_treated_as_known_false():
    module = warnings_module()
    missing = module.build_warnings(listing(position=None), None)
    unknown = module.build_warnings(
        listing(position=Position(lat=10.01, lng=105.77, precision="UNKNOWN")), None
    )
    verified = module.build_warnings(
        listing(position=Position(lat=10.01, lng=105.77, precision="VERIFIED",
                                  source="survey", verified_at="2026-10-04T08:00:00+07:00")),
        route(mode="BUS", evidence="LIVE"),
    )

    assert "LOCATION_UNKNOWN" in codes(missing)
    assert "LOCATION_UNKNOWN" in codes(unknown)
    assert "APPROXIMATE_LOCATION" not in codes(unknown)
    assert "APPROXIMATE_LOCATION" not in codes(verified)
    assert "LOCATION_UNKNOWN" not in codes(verified)


def test_provisional_campus_and_unverified_route_are_warned_separately():
    warnings = warnings_module().build_warnings(listing(), route(mode="BUS", status="NO_ROUTE", evidence="NONE"))

    by_code = {warning.code: warning for warning in warnings}
    assert "ENTRANCE_UNVERIFIED" in by_code
    assert by_code["ENTRANCE_UNVERIFIED"].scope == "campus"
    assert "ROUTE_NOT_VERIFIED" in by_code
    assert by_code["ROUTE_NOT_VERIFIED"].scope == "route"


@pytest.mark.parametrize("mode", ["WALK", "BICYCLE", "MOTORBIKE"])
def test_displayed_google_beta_route_carries_documented_caution(mode):
    warnings = warnings_module().build_warnings(
        listing(), route(mode=mode, status="OK", evidence="LIVE")
    )
    beta = [warning for warning in warnings if warning.code == "GOOGLE_ROUTE_BETA"]

    assert len(beta) == 1
    assert beta[0].severity == "CAUTION"
    assert beta[0].scope == "route"
    assert "vỉa hè" in beta[0].message.lower() or "lối đi" in beta[0].message.lower()


def test_beta_warning_does_not_apply_to_bus_other_provider_or_failed_route():
    module = warnings_module()

    bus = module.build_warnings(listing(), route(mode="BUS", evidence="LIVE"))
    other_provider = module.build_warnings(listing(), route(provider="ors", evidence="LIVE"))
    failed = module.build_warnings(listing(), route(status="PROVIDER_ERROR", evidence="NONE"))

    assert "GOOGLE_ROUTE_BETA" not in codes(bus)
    assert "GOOGLE_ROUTE_BETA" not in codes(other_provider)
    assert "GOOGLE_ROUTE_BETA" not in codes(failed)


def test_police_proximity_and_route_success_never_verify_approximate_listing_coordinates():
    warnings = warnings_module().build_warnings(
        listing(parsed_amenities={"police": True}), route(mode="WALK", evidence="LIVE")
    )
    by_code = {warning.code: warning for warning in warnings}

    assert "APPROXIMATE_LOCATION" in by_code
    assert "SECURITY_SCORE" not in codes(warnings)
    assert "ML_SAFETY_PROBABILITY" not in codes(warnings)
    assert set(by_code["APPROXIMATE_LOCATION"].model_dump()) == {
        "code", "severity", "message", "evidence_source", "scope", "observed_at",
    }


def test_explicitly_complete_description_and_verified_listing_flags_do_not_warn():
    warnings = warnings_module().build_warnings(
        listing(
            description_state="COMPLETE",
            description_is_partial=False,
            unit_type_uncertain=False,
            lease_transfer_terms_verified=True,
            position=Position(lat=10.01, lng=105.77, precision="VERIFIED",
                              source="survey", verified_at="2026-10-04T08:00:00+07:00"),
        ),
        route(mode="BUS", evidence="LIVE"),
    )

    assert not ({"PARTIAL_DESCRIPTION", "UNIT_TYPE_UNKNOWN", "TRANSFER_TERMS_UNVERIFIED",
                 "APPROXIMATE_LOCATION", "LOCATION_UNKNOWN", "ROUTE_NOT_VERIFIED"} & codes(warnings))
