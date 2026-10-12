from datetime import datetime, timezone

import pytest
from pydantic import SecretStr


def test_demo_policy_manifest_has_exact_live_provider_contract():
    from app.mobility.providers.demo_policy import (
        DEMO_ENDPOINTS,
        demo_expected_policy_hashes,
        demo_provider_policies,
    )

    policies = demo_provider_policies()
    expected = demo_expected_policy_hashes()

    assert set(policies) == {"ors", "osm_overpass", "nominatim"}
    assert set(expected) == set(policies)
    assert DEMO_ENDPOINTS == {
        "ors": "https://api.heigit.org",
        "osm_overpass": "https://overpass-api.de",
        "nominatim": "https://nominatim.openstreetmap.org",
    }
    assert policies["ors"].allowed_paths == (
        "/openrouteservice/v2/directions/foot-walking/geojson",
        "/openrouteservice/v2/directions/cycling-regular/geojson",
    )
    assert policies["ors"].allowed_capabilities == ("route:WALK", "route:BICYCLE")
    assert policies["osm_overpass"].allowed_paths == ("/api/interpreter",)
    assert policies["nominatim"].allowed_paths == ("/search",)
    assert all(policy.max_requests == 30 for policy in policies.values())
    assert all(policy.max_rps == 1.0 and policy.max_concurrency == 1 for policy in policies.values())
    assert all(policy.approved_until == datetime(2026, 12, 31, tzinfo=timezone.utc) for policy in policies.values())
    assert all(expected[name] == policies[name].policy_sha256 for name in policies)


def test_demo_policy_digest_is_independently_valid():
    from app.mobility.providers.demo_policy import (
        demo_expected_policy_hashes,
        demo_provider_policies,
    )
    from app.mobility.providers.network_policy import policy_digest

    policies = demo_provider_policies()
    expected = demo_expected_policy_hashes()
    assert {name: policy_digest(policy) for name, policy in policies.items()} == expected


def test_live_settings_use_demo_policy_only_when_explicitly_enabled():
    from app.mobility.providers.demo_policy import build_demo_live_settings

    disabled = build_demo_live_settings(enabled=True, live_enabled=False)
    assert disabled.live_enabled is False
    assert disabled.provider_policies == {}
    assert disabled.expected_policy_hashes == {}

    enabled = build_demo_live_settings(
        enabled=True,
        live_enabled=True,
        ors_api_key=SecretStr("runtime-only-ors-key"),
    )
    assert enabled.live_enabled is True
    assert set(enabled.provider_policies) == {"ors", "osm_overpass", "nominatim"}
    assert enabled.ors_base_url == "https://api.heigit.org"
    assert enabled.overpass_url == "https://overpass-api.de/api/interpreter"
    assert enabled.nominatim_url == "https://nominatim.openstreetmap.org"
    assert enabled.ors_api_key.get_secret_value() == "runtime-only-ors-key"
    assert enabled.tiles_enabled is True
    assert enabled.tile_url == "https://tile.openstreetmap.org/{z}/{x}/{y}.png"
    assert enabled.allowed_tile_origin == "https://tile.openstreetmap.org"
    assert "runtime-only-ors-key" not in repr(enabled)


def test_trusted_hashes_are_independent_from_policy_objects():
    from app.mobility.providers import demo_policy

    policies = demo_policy.demo_provider_policies()
    trusted = demo_policy.demo_expected_policy_hashes()
    assert trusted == {
        "ors": "4a27be530410ebf6267c23f80d1ccecf55ada27dbd739579557bfe14562b571b",
        "osm_overpass": "7c22f1cf047bbb5f2fc303fb73d74211e2da71a98abbcbf066e200b05ff51725",
        "nominatim": "7f305b9509d84beb93573beb20808b8fe11d50630864d96d82f8889c4844133f",
    }
    assert all(trusted[name] == policy.policy_sha256 for name, policy in policies.items())
    assert trusted is not demo_policy._POLICY_HASHES
    assert trusted == demo_policy._TRUSTED_POLICY_HASHES
