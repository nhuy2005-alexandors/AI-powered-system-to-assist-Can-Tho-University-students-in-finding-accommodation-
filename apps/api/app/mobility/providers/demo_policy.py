"""Trusted, bounded provider policy for the local catalog demo.

The manifest is deliberately code-bound. Provider endpoints, paths, budgets and
expiry are reviewed together; credentials remain environment-only.
"""

from datetime import datetime, timezone

from .network_policy import ProviderPolicy
from .open_config import OpenMobilitySettings


DEMO_ENDPOINTS = {
    "ors": "https://api.heigit.org",
    "osm_overpass": "https://overpass-api.de",
    "nominatim": "https://nominatim.openstreetmap.org",
}

_APPROVED_UNTIL = datetime(2026, 12, 31, tzinfo=timezone.utc)
_USER_AGENT = "NCKH-Tro-CTU/0.1"
_POLICY_HASHES = {
    "ors": "4a27be530410ebf6267c23f80d1ccecf55ada27dbd739579557bfe14562b571b",
    "osm_overpass": "7c22f1cf047bbb5f2fc303fb73d74211e2da71a98abbcbf066e200b05ff51725",
    "nominatim": "7f305b9509d84beb93573beb20808b8fe11d50630864d96d82f8889c4844133f",
}
_TRUSTED_POLICY_HASHES = {
    "ors": "4a27be530410ebf6267c23f80d1ccecf55ada27dbd739579557bfe14562b571b",
    "osm_overpass": "7c22f1cf047bbb5f2fc303fb73d74211e2da71a98abbcbf066e200b05ff51725",
    "nominatim": "7f305b9509d84beb93573beb20808b8fe11d50630864d96d82f8889c4844133f",
}


def demo_provider_policies() -> dict[str, ProviderPolicy]:
    common = {
        "cache_policy": "NO_CACHE_ALLOWED",
        "approved_until": _APPROVED_UNTIL,
        "max_requests": 30,
        "max_rps": 1.0,
        "max_concurrency": 1,
        "timeout_seconds": 10.0,
        "connect_timeout_seconds": 2.0,
        "max_response_bytes": 1_048_576,
    }
    return {
        "ors": ProviderPolicy(
            provider="ors",
            base_url=DEMO_ENDPOINTS["ors"],
            allowed_paths=(
                "/openrouteservice/v2/directions/foot-walking/geojson",
                "/openrouteservice/v2/directions/cycling-regular/geojson",
            ),
            allowed_capabilities=("route:WALK", "route:BICYCLE"),
            attribution=("openrouteservice / HeiGIT",),
            user_agent=_USER_AGENT,
            policy_sha256=_POLICY_HASHES["ors"],
            **common,
        ),
        "osm_overpass": ProviderPolicy(
            provider="osm_overpass",
            base_url=DEMO_ENDPOINTS["osm_overpass"],
            allowed_paths=("/api/interpreter",),
            allowed_capabilities=("nearby",),
            attribution=("OpenStreetMap contributors", "Overpass API"),
            user_agent=_USER_AGENT,
            policy_sha256=_POLICY_HASHES["osm_overpass"],
            **common,
        ),
        "nominatim": ProviderPolicy(
            provider="nominatim",
            base_url=DEMO_ENDPOINTS["nominatim"],
            allowed_paths=("/search",),
            allowed_capabilities=("geocode",),
            attribution=("OpenStreetMap contributors", "Nominatim"),
            user_agent="NCKH-Tro-CTU/0.1 (+https://github.com/nhuy2005-alexandors)",
            policy_sha256=_POLICY_HASHES["nominatim"],
            **(common | {"cache_policy": "MEMORY_24H"}),
        ),
    }


def demo_expected_policy_hashes() -> dict[str, str]:
    return dict(_TRUSTED_POLICY_HASHES)


def build_demo_live_settings(*, enabled: bool, live_enabled: bool, ors_api_key=None) -> OpenMobilitySettings:
    if not live_enabled:
        return OpenMobilitySettings(enabled=enabled, live_enabled=False)
    return OpenMobilitySettings(
        enabled=enabled,
        live_enabled=True,
        routing_provider="ors",
        places_provider="osm_overpass",
        geocoder_provider="nominatim",
        ors_base_url=DEMO_ENDPOINTS["ors"],
        overpass_url=f"{DEMO_ENDPOINTS['osm_overpass']}/api/interpreter",
        nominatim_url=DEMO_ENDPOINTS["nominatim"],
        ors_api_key=ors_api_key,
        provider_policies=demo_provider_policies(),
        expected_policy_hashes=demo_expected_policy_hashes(),
        tiles_enabled=True,
        tile_url="https://tile.openstreetmap.org/{z}/{x}/{y}.png",
        tile_attribution="© OpenStreetMap contributors",
        allowed_tile_origin="https://tile.openstreetmap.org",
    )
