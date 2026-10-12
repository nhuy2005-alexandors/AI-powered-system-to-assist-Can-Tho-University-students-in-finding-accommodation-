"""Offline-only Google Routes adapter; fixture transport is the only allowed wire."""
import asyncio
from datetime import datetime, timezone
import math
import re
from typing import Any

import httpx
from pydantic import ValidationError

from ..contracts import Position, ResolvedRouteRequest, RouteResult, TravelMode
from .base import MobilitySettings, request_gate


_COMPUTE_ROUTES_URL = "https://routes.googleapis.com/directions/v2:computeRoutes"
_ROUTE_FIELDS = "routes.duration,routes.distanceMeters,routes.polyline.encodedPolyline"
_BUS_FIELDS = ",routes.legs.steps.travelMode,routes.legs.steps.transitDetails.transitLine.vehicle.type"
_GOOGLE_MODES = {
    TravelMode.MOTORBIKE: "TWO_WHEELER",
    TravelMode.WALK: "WALK",
    TravelMode.BICYCLE: "BICYCLE",
    TravelMode.BUS: "TRANSIT",
}
_BUS_VEHICLES = {"BUS", "INTERCITY_BUS", "TROLLEYBUS"}
_DURATION = re.compile(r"^(?P<seconds>\d+(?:\.\d+)?)s$")


def _timestamp() -> datetime:
    return datetime.now(timezone.utc)


def _duration_seconds(value: Any) -> float:
    if not isinstance(value, str):
        raise ValueError("invalid route duration")
    match = _DURATION.fullmatch(value)
    if match is None:
        raise ValueError("invalid route duration")
    seconds = float(match.group("seconds"))
    if not math.isfinite(seconds) or seconds < 0:
        raise ValueError("invalid route duration")
    return seconds


def _distance_meters(value: Any) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("invalid route distance")
    meters = float(value)
    if not math.isfinite(meters) or meters < 0:
        raise ValueError("invalid route distance")
    return meters


def _decode_value(encoded: str, index: int) -> tuple[int, int]:
    result = 0
    shift = 0
    while True:
        if index >= len(encoded):
            raise ValueError("truncated encoded polyline")
        chunk = ord(encoded[index]) - 63
        if chunk < 0 or chunk > 63:
            raise ValueError("invalid encoded polyline character")
        index += 1
        result |= (chunk & 0x1F) << shift
        shift += 5
        if shift > 35:
            raise ValueError("encoded polyline value is too large")
        if chunk < 0x20:
            break
    delta = ~(result >> 1) if result & 1 else result >> 1
    return delta, index


def _decode_polyline(value: Any) -> list[Position]:
    if not isinstance(value, str) or not value:
        raise ValueError("invalid encoded polyline")
    points: list[Position] = []
    latitude = longitude = 0
    index = 0
    while index < len(value):
        latitude_delta, index = _decode_value(value, index)
        longitude_delta, index = _decode_value(value, index)
        latitude += latitude_delta
        longitude += longitude_delta
        points.append(Position(lat=latitude / 100_000, lng=longitude / 100_000))
    return points


def _validate_bus_legs(route: dict[str, Any]) -> None:
    legs = route.get("legs")
    if not isinstance(legs, list) or not legs:
        raise ValueError("missing transit evidence")

    transit_steps: list[dict[str, Any]] = []
    for leg in legs:
        if not isinstance(leg, dict):
            raise ValueError("malformed transit leg")
        steps = leg.get("steps")
        if not isinstance(steps, list) or not steps:
            raise ValueError("missing transit steps")
        for step in steps:
            if not isinstance(step, dict):
                raise ValueError("malformed transit step")
            step_mode = step.get("travelMode")
            if step_mode == "TRANSIT":
                transit_steps.append(step)
            elif step_mode != "WALK":
                raise ValueError("BUS route contains a non-walking access step")

    if not transit_steps:
        raise ValueError("BUS route lacks a transit step")
    for step in transit_steps:
        transit_details = step.get("transitDetails")
        transit_line = transit_details.get("transitLine") if isinstance(transit_details, dict) else None
        vehicle = transit_line.get("vehicle") if isinstance(transit_line, dict) else None
        vehicle_type = vehicle.get("type") if isinstance(vehicle, dict) else None
        if vehicle_type not in _BUS_VEHICLES:
            raise ValueError("transit vehicle is not a documented bus type")


class GoogleRoutesProvider:
    def __init__(self, config: MobilitySettings, transport: httpx.AsyncBaseTransport | None = None):
        self._config = config
        self._transport = transport

    def _result(
        self,
        request: ResolvedRouteRequest,
        status: str,
        *,
        observed_at: datetime | None = None,
        evidence_kind: str = "NONE",
    ) -> RouteResult:
        return RouteResult(
            listing_id=request.request.listing_id,
            campus_id=request.request.campus_id,
            provider="google",
            attribution=["Google Maps Platform"] if evidence_kind != "NONE" else [],
            provider_profile=None,
            requested_mode=request.request.requested_mode,
            status=status,
            coordinate_version=request.destination.coordinate_version,
            observed_at=observed_at,
            evidence_kind=evidence_kind,
        )

    async def compute_route(self, request: ResolvedRouteRequest) -> RouteResult:
        mode = request.request.requested_mode
        google_mode = _GOOGLE_MODES.get(mode)
        if google_mode is None:
            return self._result(request, "UNSUPPORTED_MODE")

        gated_status = request_gate(self._config, mode.value, self._transport)
        if gated_status is not None:
            return self._result(request, gated_status)

        body: dict[str, Any] = {
            "origin": {"location": {"latLng": {
                "latitude": request.origin.lat,
                "longitude": request.origin.lng,
            }}},
            "destination": {"location": {"latLng": {
                "latitude": request.destination.lat,
                "longitude": request.destination.lng,
            }}},
            "travelMode": google_mode,
        }
        if request.request.departure_time is not None:
            departure = request.request.departure_time.astimezone(timezone.utc)
            body["departureTime"] = departure.isoformat().replace("+00:00", "Z")
        field_mask = _ROUTE_FIELDS
        if mode == TravelMode.BUS:
            body["transitPreferences"] = {"allowedTravelModes": ["BUS"]}
            field_mask += _BUS_FIELDS

        observed_at = _timestamp()
        try:
            async with httpx.AsyncClient(
                transport=self._transport,
                timeout=self._config.timeout_seconds,
            ) as client:
                response = await asyncio.wait_for(
                    client.post(
                        _COMPUTE_ROUTES_URL,
                        json=body,
                        headers={
                            "X-Goog-Api-Key": self._config.server_api_key.get_secret_value(),
                            "X-Goog-FieldMask": field_mask,
                        },
                    ),
                    timeout=self._config.timeout_seconds,
                )
        except (httpx.HTTPError, asyncio.TimeoutError):
            return self._result(
                request,
                "PROVIDER_ERROR",
                observed_at=observed_at,
                evidence_kind="SYNTHETIC_FIXTURE",
            )

        if response.status_code == 429:
            return self._result(
                request,
                "RATE_LIMITED",
                observed_at=observed_at,
                evidence_kind="SYNTHETIC_FIXTURE",
            )
        if response.status_code < 200 or response.status_code >= 300:
            return self._result(
                request,
                "PROVIDER_ERROR",
                observed_at=observed_at,
                evidence_kind="SYNTHETIC_FIXTURE",
            )

        try:
            payload = response.json()
        except (ValueError, TypeError):
            return self._result(
                request,
                "PROVIDER_ERROR",
                observed_at=observed_at,
                evidence_kind="SYNTHETIC_FIXTURE",
            )

        if not isinstance(payload, dict) or not isinstance(payload.get("routes"), list):
            return self._result(
                request,
                "PROVIDER_ERROR",
                observed_at=observed_at,
                evidence_kind="SYNTHETIC_FIXTURE",
            )
        routes = payload["routes"]
        if not routes:
            return self._result(
                request,
                "NO_ROUTE",
                observed_at=observed_at,
                evidence_kind="SYNTHETIC_FIXTURE",
            )

        try:
            route = routes[0]
            if not isinstance(route, dict):
                raise ValueError("malformed route")
            if mode == TravelMode.BUS:
                _validate_bus_legs(route)
            duration = _duration_seconds(route.get("duration"))
            distance = _distance_meters(route.get("distanceMeters"))
            encoded_polyline = None
            if "polyline" in route:
                raw_polyline = route["polyline"]
                if not isinstance(raw_polyline, dict) or "encodedPolyline" not in raw_polyline:
                    raise ValueError("malformed route polyline")
                encoded_polyline = raw_polyline["encodedPolyline"]
            points = None if encoded_polyline is None else _decode_polyline(encoded_polyline)
            return RouteResult(
                listing_id=request.request.listing_id,
                campus_id=request.request.campus_id,
                provider="google",
                attribution=["Google Maps Platform"],
                provider_profile=None,
                requested_mode=mode,
                effective_mode=mode,
                status="OK",
                duration_seconds=duration,
                distance_meters=distance,
                polyline=points,
                observed_at=observed_at,
                coordinate_version=request.destination.coordinate_version,
                evidence_kind="SYNTHETIC_FIXTURE",
            )
        except (TypeError, ValueError, OverflowError, ValidationError):
            return self._result(
                request,
                "PROVIDER_ERROR",
                observed_at=observed_at,
                evidence_kind="SYNTHETIC_FIXTURE",
            )
