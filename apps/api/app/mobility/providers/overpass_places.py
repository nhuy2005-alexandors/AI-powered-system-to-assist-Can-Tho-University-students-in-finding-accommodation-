"""Offline-safe query construction and policy-gated Overpass places adapter."""
import json
import math
from urllib.parse import urlsplit

import httpx

from ..contracts import NearbyResult, Place, ResolvedNearbyRequest
from .network_policy import RequestPolicyError
from .open_config import OpenMobilitySettings


_CATEGORY_ORDER = (
    "grocery",
    "market",
    "pharmacy",
    "healthcare",
    "police",
    "bus_stop",
)

_CATEGORY_SELECTORS = {
    "grocery": (
        (("shop", "supermarket"),),
        (("shop", "convenience"),),
    ),
    "market": ((("amenity", "marketplace"),),),
    "pharmacy": ((("amenity", "pharmacy"),),),
    "healthcare": (
        (("amenity", "hospital"),),
        (("amenity", "clinic"),),
        (("amenity", "doctors"),),
    ),
    "police": ((("amenity", "police"),),),
    "bus_stop": (
        (("highway", "bus_stop"),),
        (("public_transport", "platform"), ("bus", "yes")),
    ),
}


def _coordinate(value: object, *, minimum: float, maximum: float) -> str:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("nearby center must contain numeric coordinates")
    number = float(value)
    if not math.isfinite(number) or not minimum <= number <= maximum:
        raise ValueError("nearby center coordinate is outside its valid range")
    return str(number)


def build_overpass_query(request: ResolvedNearbyRequest) -> str:
    """Build one bounded Overpass QL request from validated server-resolved data."""
    if not isinstance(request, ResolvedNearbyRequest):
        raise TypeError("Overpass query requires a resolved nearby request")

    radius = request.request.radius_m
    if radius not in (500, 1000, 2000):
        raise ValueError("nearby radius is not supported")
    latitude = _coordinate(request.center.lat, minimum=-90, maximum=90)
    longitude = _coordinate(request.center.lng, minimum=-180, maximum=180)

    requested_categories = set(request.request.categories)
    unknown_categories = requested_categories.difference(_CATEGORY_ORDER)
    if unknown_categories:
        raise ValueError("nearby request contains an unsupported category")
    if not requested_categories:
        raise ValueError("nearby request must select at least one category")

    selectors: list[tuple[tuple[str, str], ...]] = []
    for category in _CATEGORY_ORDER:
        if category in requested_categories:
            for selector in _CATEGORY_SELECTORS[category]:
                if selector not in selectors:
                    selectors.append(selector)

    clauses = []
    for selector in selectors:
        tags = "".join(f'["{key}"="{value}"]' for key, value in selector)
        clauses.append(
            f"  nwr(around:{radius},{latitude},{longitude}){tags};"
        )

    return "\n".join((
        "[out:json][timeout:8];",
        "(",
        *clauses,
        ");",
        "out center 101;",
    ))


_EARTH_RADIUS_METERS = 6_371_000.0
_ELEMENT_TYPE_ORDER = {"node": 0, "way": 1, "relation": 2}
_ODBL_ATTRIBUTION = "Data licensed under the Open Database License (ODbL)"
_UNNAMED_PLACE_LABEL = "Unnamed OpenStreetMap place"
_OVERPASS_PATH = "/api/interpreter"


class _MalformedOverpassResponse(ValueError):
    """Provider response cannot establish a valid nearby result."""


def _number(value: object) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise _MalformedOverpassResponse
    result = float(value)
    if not math.isfinite(result):
        raise _MalformedOverpassResponse
    return result


def _element_position(element: dict) -> tuple[float, float]:
    element_type = element.get("type")
    if element_type == "node":
        lat_value, lon_value = element.get("lat"), element.get("lon")
    elif element_type in ("way", "relation"):
        center = element.get("center")
        if not isinstance(center, dict):
            raise _MalformedOverpassResponse
        lat_value, lon_value = center.get("lat"), center.get("lon")
    else:
        raise _MalformedOverpassResponse

    latitude, longitude = _number(lat_value), _number(lon_value)
    if not -90 <= latitude <= 90 or not -180 <= longitude <= 180:
        raise _MalformedOverpassResponse
    return latitude, longitude


def _category_for(tags: dict[str, str], requested: set[str]) -> str | None:
    matches = {
        "grocery": tags.get("shop") in {"supermarket", "convenience"},
        "market": tags.get("amenity") == "marketplace",
        "pharmacy": tags.get("amenity") == "pharmacy",
        "healthcare": tags.get("amenity") in {"hospital", "clinic", "doctors"},
        "police": tags.get("amenity") == "police",
        "bus_stop": (
            tags.get("highway") == "bus_stop"
            or (tags.get("public_transport") == "platform" and tags.get("bus") == "yes")
        ),
    }
    return next((category for category in _CATEGORY_ORDER
                 if category in requested and matches[category]), None)


def _distance_meters(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    haversine = (
        math.sin(delta_phi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
    )
    return 2 * _EARTH_RADIUS_METERS * math.asin(min(1.0, math.sqrt(haversine)))


def _endpoint_attribution(settings: OpenMobilitySettings) -> list[str]:
    policy = settings.provider_policies.get("osm_overpass")
    if policy is None or _OVERPASS_PATH not in policy.allowed_paths:
        raise _MalformedOverpassResponse
    parts = urlsplit(policy.base_url)
    hostname = parts.hostname
    if parts.scheme.lower() != "https" or not hostname:
        raise _MalformedOverpassResponse
    authority = f"[{hostname}]" if ":" in hostname else hostname
    if parts.port is not None:
        authority = f"{authority}:{parts.port}"
    endpoint = f"https://{authority}{_OVERPASS_PATH}"
    policy_attribution = list(policy.attribution)
    values = [*policy_attribution, _ODBL_ATTRIBUTION, f"Overpass endpoint: {endpoint}"]
    return list(dict.fromkeys(values))


def _parse_elements(
    elements: object,
    request: ResolvedNearbyRequest,
    attribution: list[str],
) -> tuple[list[Place], bool]:
    if not isinstance(elements, list) or len(elements) > 101:
        raise _MalformedOverpassResponse

    center_lat = _number(request.center.lat)
    center_lon = _number(request.center.lng)
    radius = request.request.radius_m
    requested = set(request.request.categories)
    cap_reached = len(elements) >= 101
    seen: dict[str, tuple[tuple, Place | None]] = {}
    candidates: list[tuple[int, int, int, Place]] = []

    for element in elements:
        if not isinstance(element, dict):
            raise _MalformedOverpassResponse
        element_type = element.get("type")
        element_id = element.get("id")
        if (element_type not in _ELEMENT_TYPE_ORDER or isinstance(element_id, bool)
                or not isinstance(element_id, int) or element_id <= 0):
            raise _MalformedOverpassResponse
        latitude, longitude = _element_position(element)
        tags = element.get("tags")
        if (not isinstance(tags, dict)
                or any(not isinstance(key, str) or not isinstance(value, str)
                       for key, value in tags.items())):
            raise _MalformedOverpassResponse

        identity = f"{element_type}:{element_id}"
        signature = (latitude, longitude, tuple(sorted(tags.items())))
        category = _category_for(tags, requested)
        distance = _distance_meters(center_lat, center_lon, latitude, longitude)
        place = None
        if category is not None and distance <= radius:
            name = tags.get("name")
            display_name = name.strip() if isinstance(name, str) else ""
            place = Place(
                provider_place_id=identity,
                name=display_name or _UNNAMED_PLACE_LABEL,
                category=category,
                lat=latitude,
                lng=longitude,
                straight_line_distance_m=distance,
                attribution=attribution,
            )

        previous = seen.get(identity)
        if previous is not None:
            previous_signature, previous_place = previous
            if previous_signature != signature:
                raise _MalformedOverpassResponse
            continue
        seen[identity] = (signature, place)
        if place is not None:
            candidates.append((
                _CATEGORY_ORDER.index(category),
                _ELEMENT_TYPE_ORDER[element_type],
                element_id,
                place,
            ))

    candidates.sort(key=lambda row: row[:3])
    truncated = cap_reached or len(candidates) > 100
    places = [row[3] for row in candidates[:100]]
    if not places and cap_reached:
        # A capped response cannot prove that the requested area was empty.
        raise _MalformedOverpassResponse
    return places, truncated


class OverpassPlacesProvider:
    """Overpass adapter which sends only through the shared approved policy gate."""

    def __init__(
        self,
        settings: OpenMobilitySettings,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
    ):
        if not isinstance(settings, OpenMobilitySettings):
            raise TypeError("settings must be OpenMobilitySettings")
        self._settings = settings
        self._gate = settings.get_request_policy_gate(transport=transport)

    async def nearby(self, request: ResolvedNearbyRequest) -> NearbyResult:
        if not isinstance(request, ResolvedNearbyRequest):
            raise TypeError("nearby requires a server-resolved request")
        if (not self._settings.enabled or not self._settings.live_enabled
                or not self._settings.overpass_url
                or self._settings.places_provider != "osm_overpass"):
            return _nearby_failure(request, "NOT_CONFIGURED")

        try:
            query = build_overpass_query(request)
        except (TypeError, ValueError):
            self._gate.record_provider_failure("osm_overpass", "QUERY_INVALID")
            return _nearby_failure(request, "PROVIDER_ERROR")

        try:
            async with self._gate.claim(
                "osm_overpass", "nearby", _OVERPASS_PATH
            ) as permit:
                response = await permit.send("POST", form={"data": query})
        except RequestPolicyError as exc:
            self._gate.record_provider_failure("osm_overpass", "POLICY_OR_TRANSPORT")
            return _nearby_failure(request, exc.status)

        if response.status_code == 429:
            self._gate.record_provider_failure("osm_overpass", "RATE_LIMITED")
            return _nearby_failure(
                request, "RATE_LIMITED", response.observed_at, response.evidence_kind
            )
        if response.status_code != 200:
            self._gate.record_provider_failure("osm_overpass", "HTTP_NON_200")
            return _nearby_failure(
                request, "PROVIDER_ERROR", response.observed_at, response.evidence_kind
            )

        try:
            payload = json.loads(response.body)
            if (not isinstance(payload, dict) or "remark" in payload
                    or payload.get("error")):
                raise _MalformedOverpassResponse
            osm3s = payload.get("osm3s")
            if "osm3s" in payload and not isinstance(osm3s, dict):
                raise _MalformedOverpassResponse
            if isinstance(osm3s, dict) and "remark" in osm3s:
                raise _MalformedOverpassResponse
            places, truncated = _parse_elements(
                payload.get("elements"), request, _endpoint_attribution(self._settings)
            )
        except (ValueError, TypeError, UnicodeDecodeError, OverflowError, RecursionError):
            self._gate.record_provider_failure("osm_overpass", "MALFORMED_RESPONSE")
            return _nearby_failure(
                request, "PROVIDER_ERROR", response.observed_at, response.evidence_kind
            )

        return NearbyResult(
            listing_id=request.request.listing_id,
            radius_m=request.request.radius_m,
            categories=request.request.categories,
            provider="osm_overpass",
            status="OK" if places else "EMPTY",
            evidence_kind=response.evidence_kind,
            items=places,
            queried_at=response.observed_at,
            center_precision=request.center.precision,
            coverage="PARTIAL",
            truncated=truncated,
        )


def _nearby_failure(
    request: ResolvedNearbyRequest,
    status: str,
    queried_at=None,
    evidence_kind: str = "NONE",
) -> NearbyResult:
    return NearbyResult(
        listing_id=request.request.listing_id,
        radius_m=request.request.radius_m,
        categories=request.request.categories,
        provider="osm_overpass",
        status=status,
        evidence_kind=evidence_kind,
        items=[],
        queried_at=queried_at,
        center_precision=request.center.precision,
        coverage="UNKNOWN",
        truncated=False,
    )
