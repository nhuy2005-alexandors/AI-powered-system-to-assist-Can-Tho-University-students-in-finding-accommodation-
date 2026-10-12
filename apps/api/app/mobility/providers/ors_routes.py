"""OpenRouteService directions adapter behind the shared mobility request gate."""
import json
import math
from typing import Any

import httpx

from ..contracts import ResolvedRouteRequest, RouteResult
from .network_policy import ProviderResponse, RequestPolicyError
from .open_config import OpenMobilitySettings


_ROUTES = {
    "WALK": ("foot-walking", "/openrouteservice/v2/directions/foot-walking/geojson"),
    "BICYCLE": ("cycling-regular", "/openrouteservice/v2/directions/cycling-regular/geojson"),
}


class ORSRouteProvider:
    def __init__(
        self,
        settings: OpenMobilitySettings,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
    ):
        self._settings = settings
        self._transport = transport
        self._gate = settings.get_request_policy_gate(transport=transport)

    async def compute_route(self, request: ResolvedRouteRequest) -> RouteResult:
        mode = request.request.requested_mode
        route = _ROUTES.get(mode)
        if route is None:
            return self._result(request, "UNSUPPORTED_MODE")

        profile, path = route
        if (not self._settings.enabled or not self._settings.live_enabled or
                self._settings.routing_provider != "ors" or not self._settings.ors_base_url or
                not self._settings.ors_api_key.get_secret_value()):
            return self._result(request, "NOT_CONFIGURED", profile=profile)

        capability = f"route:{mode.value}"
        coordinates = [
            [request.origin.lng, request.origin.lat],
            [request.destination.lng, request.destination.lat],
        ]
        try:
            async with self._gate.claim("ors", capability, path) as permit:
                response = await permit.send("POST", json_body={"coordinates": coordinates})
        except RequestPolicyError as exc:
            return self._result(request, exc.status, profile=profile)

        if response.status_code == 429:
            return self._result(request, "RATE_LIMITED", profile=profile, response=response)
        if response.status_code != 200:
            if response.status_code >= 300 and _is_explicit_no_route(response.body):
                return self._result(request, "NO_ROUTE", profile=profile, response=response)
            return self._result(request, "PROVIDER_ERROR", profile=profile, response=response)

        parsed = self._parse_route(response.body)
        if parsed is None:
            return self._result(request, "PROVIDER_ERROR", profile=profile, response=response)

        duration, distance, geometry = parsed
        return self._result(
            request,
            "OK",
            profile=profile,
            response=response,
            duration=duration,
            distance=distance,
            geometry=geometry,
        )

    def _result(
        self,
        request: ResolvedRouteRequest,
        status: str,
        *,
        profile: str | None = None,
        response: ProviderResponse | None = None,
        duration: float | None = None,
        distance: float | None = None,
        geometry=None,
    ) -> RouteResult:
        policy = self._settings.provider_policies.get("ors")
        attribution = [] if response is None or policy is None else list(policy.attribution)
        return RouteResult(
            listing_id=request.request.listing_id,
            campus_id=request.request.campus_id,
            provider="ors",
            attribution=attribution,
            provider_profile=profile,
            requested_mode=request.request.requested_mode,
            effective_mode=request.request.requested_mode if status == "OK" else None,
            status=status,
            duration_seconds=duration,
            distance_meters=distance,
            polyline=geometry,
            observed_at=None if response is None else response.observed_at,
            coordinate_version=request.destination.coordinate_version,
            evidence_kind="NONE" if response is None else response.evidence_kind,
        )

    @staticmethod
    def _parse_route(body: bytes) -> tuple[float, float, list] | None:
        try:
            payload: Any = json.loads(body.decode("utf-8"))
        except (UnicodeDecodeError, ValueError, RecursionError):
            return None
        if not isinstance(payload, dict) or payload.get("type") != "FeatureCollection":
            return None
        features = payload.get("features")
        if not isinstance(features, list) or len(features) != 1:
            return None
        feature = features[0]
        if not isinstance(feature, dict):
            return None
        properties = feature.get("properties")
        geometry = feature.get("geometry")
        if not isinstance(properties, dict) or not isinstance(geometry, dict):
            return None
        summary = properties.get("summary")
        if not isinstance(summary, dict):
            return None
        distance = _finite_nonnegative(summary.get("distance"))
        duration = _finite_nonnegative(summary.get("duration"))
        if distance is None or duration is None or geometry.get("type") != "LineString":
            return None
        coordinates = geometry.get("coordinates")
        if not isinstance(coordinates, list) or len(coordinates) < 2:
            return None

        from ..contracts import Position

        points = []
        for coordinate in coordinates:
            if not isinstance(coordinate, list) or len(coordinate) != 2:
                return None
            longitude = _finite_number(coordinate[0])
            latitude = _finite_number(coordinate[1])
            if (longitude is None or latitude is None or not -180 <= longitude <= 180 or
                    not -90 <= latitude <= 90):
                return None
            points.append(Position(lat=latitude, lng=longitude))
        return duration, distance, points


def _finite_number(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    try:
        number = float(value)
    except (OverflowError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _finite_nonnegative(value: Any) -> float | None:
    number = _finite_number(value)
    return number if number is not None and number >= 0 else None


def _is_explicit_no_route(body: bytes) -> bool:
    try:
        payload = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, ValueError, RecursionError):
        return False
    if not isinstance(payload, dict) or not isinstance(payload.get("error"), dict):
        return False
    message = payload["error"].get("message")
    if not isinstance(message, str):
        return False
    normalized = " ".join(message.casefold().split())
    return (
        normalized == "route could not be found" or
        normalized.startswith("unable to find a route between ")
    )
