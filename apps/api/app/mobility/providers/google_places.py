"""Bounded Google Places adapter, exercised only with injected offline transports."""
from datetime import datetime, timezone
import asyncio
import math
from urllib.parse import urlparse

import httpx
from pydantic import ValidationError

from ..contracts import NearbyResult, Place, PlaceCategory, ResolvedNearbyRequest
from .base import MobilitySettings, request_gate


_SEARCH_URL = "https://places.googleapis.com/v1/places:searchNearby"
_MAX_RESULTS = 20
_FIELD_MASK = "places.id,places.displayName,places.location,places.types,places.attributions"
_EARTH_RADIUS_METERS = 6_371_000.0

# This bounded mapping is grounded in the official Place Types Table A evidence
# captured for the offline foundation. It says nothing about live city coverage.
_CATEGORY_TYPES: dict[PlaceCategory, tuple[str, ...]] = {
    "grocery": ("grocery_store", "supermarket"),
    "market": ("market",),
    "pharmacy": ("pharmacy",),
    "healthcare": ("hospital", "medical_clinic"),
    "police": ("police",),
    "bus_stop": ("bus_stop",),
}


class _MalformedPlacesResponse(ValueError):
    """Internal marker; provider response details never escape this module."""


class GooglePlacesProvider:
    def __init__(self, config: MobilitySettings,
                 transport: httpx.AsyncBaseTransport | None = None):
        self._config = config
        self._transport = transport

    async def nearby(self, request: ResolvedNearbyRequest) -> NearbyResult:
        nearby = request.request
        categories = list(nearby.categories)

        # Fail closed for any missing mapping or unverified requested category.
        if any(category not in _CATEGORY_TYPES for category in categories):
            return self._result(request, "CAPABILITY_UNVERIFIED")
        if any(request_gate(self._config, category, self._transport, nearby=True)
               is not None for category in categories):
            return self._result(request, request_gate(
                self._config, categories[0], self._transport, nearby=True
            ) or "CAPABILITY_UNVERIFIED")

        included_types = list(dict.fromkeys(
            wire_type
            for category in categories
            for wire_type in _CATEGORY_TYPES[category]
        ))
        payload = {
            "includedTypes": included_types,
            "maxResultCount": _MAX_RESULTS,
            "locationRestriction": {
                "circle": {
                    "center": {
                        "latitude": request.center.lat,
                        "longitude": request.center.lng,
                    },
                    "radius": nearby.radius_m,
                }
            },
        }
        queried_at = datetime.now(timezone.utc)
        evidence_kind = "SYNTHETIC_FIXTURE" if isinstance(self._transport, httpx.MockTransport) else "NONE"
        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": self._config.server_api_key.get_secret_value(),
            "X-Goog-FieldMask": _FIELD_MASK,
        }

        try:
            async with httpx.AsyncClient(
                transport=self._transport,
                timeout=self._config.timeout_seconds,
            ) as client:
                response = await asyncio.wait_for(
                    client.post(_SEARCH_URL, headers=headers, json=payload),
                    timeout=self._config.timeout_seconds,
                )
        except (httpx.HTTPError, TimeoutError):
            return self._result(request, "PROVIDER_ERROR", evidence_kind=evidence_kind,
                                queried_at=queried_at)

        if response.status_code == 429:
            return self._result(request, "RATE_LIMITED", evidence_kind=evidence_kind,
                                queried_at=queried_at)
        if not 200 <= response.status_code < 300:
            return self._result(request, "PROVIDER_ERROR", evidence_kind=evidence_kind,
                                queried_at=queried_at)

        try:
            document = response.json()
            raw_places = document.get("places") if isinstance(document, dict) else None
            if not isinstance(raw_places, list):
                raise _MalformedPlacesResponse
            saturated = len(raw_places) >= _MAX_RESULTS
            # The public response schema has no page token. Honor the documented
            # twenty-place ceiling and communicate saturation without pagination.
            selected_places = raw_places[:_MAX_RESULTS]
            items = []
            for raw_place in selected_places:
                place = self._parse_place(raw_place, request)
                if place is not None:
                    items.append(place)
        except (ValueError, TypeError, KeyError, ValidationError):
            return self._result(request, "PROVIDER_ERROR", evidence_kind=evidence_kind,
                                queried_at=queried_at)

        return self._result(
            request,
            "OK" if items else "EMPTY",
            evidence_kind=evidence_kind,
            queried_at=queried_at,
            items=items,
            coverage="PARTIAL",
            truncated=saturated,
        )

    @classmethod
    def _parse_place(cls, raw: object, request: ResolvedNearbyRequest) -> Place | None:
        if not isinstance(raw, dict):
            raise _MalformedPlacesResponse

        place_id = raw.get("id")
        display_name = raw.get("displayName")
        location = raw.get("location")
        types = raw.get("types")
        if (not isinstance(place_id, str) or not place_id.strip() or
                not isinstance(display_name, dict) or
                not isinstance(display_name.get("text"), str) or
                not display_name["text"].strip() or
                not isinstance(location, dict) or
                not isinstance(types, list) or
                any(not isinstance(value, str) for value in types)):
            raise _MalformedPlacesResponse

        lat = location.get("latitude")
        lng = location.get("longitude")
        if (isinstance(lat, bool) or not isinstance(lat, (int, float)) or
                isinstance(lng, bool) or not isinstance(lng, (int, float))):
            raise _MalformedPlacesResponse
        try:
            lat = float(lat)
            lng = float(lng)
        except (OverflowError, ValueError):
            raise _MalformedPlacesResponse from None
        if (not math.isfinite(lat) or not math.isfinite(lng) or
                not -90 <= lat <= 90 or not -180 <= lng <= 180):
            raise _MalformedPlacesResponse

        category = cls._matched_category(types, request.request.categories)
        if category is None:
            # A result outside the explicit request mapping is not relabelled.
            return None

        distance = cls._distance_meters(request.center.lat, request.center.lng, float(lat), float(lng))
        if distance > request.request.radius_m:
            return None

        return Place(
            provider_place_id=place_id,
            name=display_name["text"],
            category=category,
            lat=lat,
            lng=lng,
            straight_line_distance_m=distance,
            attribution=cls._attributions(raw.get("attributions", [])),
        )

    @staticmethod
    def _matched_category(types: list[str], requested: list[PlaceCategory]) -> PlaceCategory | None:
        returned_types = set(types)
        for category in requested:
            if returned_types.intersection(_CATEGORY_TYPES.get(category, ())):
                return category
        return None

    @staticmethod
    def _attributions(value: object) -> list[str]:
        if not isinstance(value, list):
            raise _MalformedPlacesResponse
        result = []
        for entry in value:
            if not isinstance(entry, dict):
                raise _MalformedPlacesResponse
            provider = entry.get("provider")
            provider_uri = entry.get("providerUri")
            if provider is None:
                continue
            if not isinstance(provider, str) or not provider.strip():
                raise _MalformedPlacesResponse
            if provider_uri is None:
                result.append(provider)
                continue
            if not isinstance(provider_uri, str):
                raise _MalformedPlacesResponse
            parsed_uri = urlparse(provider_uri)
            if parsed_uri.scheme in ("https", "http") and parsed_uri.netloc:
                result.append(f"{provider} ({provider_uri})")
            else:
                result.append(provider)
        return result

    @staticmethod
    def _distance_meters(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
        radians = math.radians
        phi1, phi2 = radians(lat1), radians(lat2)
        delta_phi = radians(lat2 - lat1)
        delta_lambda = radians(lng2 - lng1)
        a = (math.sin(delta_phi / 2) ** 2 +
             math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2)
        return 2 * _EARTH_RADIUS_METERS * math.asin(math.sqrt(min(1.0, a)))

    @staticmethod
    def _result(request: ResolvedNearbyRequest, status: str, *,
                evidence_kind: str = "NONE", queried_at: datetime | None = None,
                items: list[Place] | None = None, coverage: str = "UNKNOWN",
                truncated: bool = False) -> NearbyResult:
        return NearbyResult(
            listing_id=request.request.listing_id,
            radius_m=request.request.radius_m,
            categories=list(request.request.categories),
            provider="google",
            status=status,
            evidence_kind=evidence_kind,
            items=items or [],
            queried_at=queried_at,
            center_precision=request.center.precision,
            coverage=coverage,
            truncated=truncated,
        )
