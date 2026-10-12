"""Bounded, policy-gated Nominatim-compatible address geocoder."""
import json
import hashlib
import math
import unicodedata
from decimal import Decimal, InvalidOperation

import httpx

from ..contracts import GeocodeRequest, GeocodeResult, Position
from .network_policy import ProviderResponse, RequestPolicyError
from .open_config import OpenMobilitySettings


_GEOCODER = "nominatim"
_CAPABILITY = "geocode"
_SEARCH_PATH = "/search"
_CEILING = (9.8, 105.4, 10.3, 106.0)  # south, west, north, east


class NominatimGeocoder:
    def __init__(
        self,
        settings: OpenMobilitySettings,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
    ):
        self._settings = settings
        self._gate = settings.get_request_policy_gate(transport=transport)

    async def geocode(self, request: GeocodeRequest) -> GeocodeResult:
        bounds = request.bounds
        south, west, north, east = _CEILING
        if (bounds.south < south or bounds.west < west or
                bounds.north > north or bounds.east > east):
            return self._result("UNSUPPORTED_REGION")

        if (not self._settings.enabled or not self._settings.live_enabled or
                self._settings.geocoder_provider != _GEOCODER or
                not self._settings.nominatim_url):
            return self._result("NOT_CONFIGURED")

        policy = self._settings.provider_policies.get(_GEOCODER)
        if policy is None or not isinstance(policy.user_agent, str) or not policy.user_agent.strip():
            return self._result("CAPABILITY_UNVERIFIED")

        normalized = " ".join(unicodedata.normalize("NFC", request.address).split())
        key = hashlib.sha256(json.dumps({
            "policy_sha256": policy.policy_sha256,
            "address": normalized,
            "bounds": bounds.model_dump(mode="json"),
        }, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode("utf-8")).hexdigest()
        try:
            return await self._gate.cached_geocode(key, lambda: self._fetch(request, normalized))
        except RequestPolicyError as exc:
            return self._result(exc.status)

    async def _fetch(self, request: GeocodeRequest, normalized: str) -> GeocodeResult:
        bounds = request.bounds
        params = {
            "format": "jsonv2",
            "limit": "5",
            "bounded": "1",
            "q": normalized,
            "viewbox": f"{bounds.west},{bounds.north},{bounds.east},{bounds.south}",
        }
        try:
            async with self._gate.claim(_GEOCODER, _CAPABILITY, _SEARCH_PATH) as permit:
                response = await permit.send("GET", params=params)
        except RequestPolicyError as exc:
            status = exc.status if exc.status in {
                "NOT_CONFIGURED", "CAPABILITY_UNVERIFIED", "RATE_LIMITED", "PROVIDER_ERROR",
            } else "PROVIDER_ERROR"
            return self._result(status)

        if response.status_code == 429:
            return self._result("RATE_LIMITED", response=response)
        if response.status_code != 200:
            return self._result("PROVIDER_ERROR", response=response)

        try:
            payload = json.loads(
                response.body.decode("utf-8"),
                object_pairs_hook=_unique_object,
                parse_constant=_reject_json_constant,
            )
        except (UnicodeDecodeError, ValueError, RecursionError, OverflowError):
            return self._result("PROVIDER_ERROR", response=response)
        positions = self._parse_candidates(payload, request)
        if positions is None:
            return self._result("PROVIDER_ERROR", response=response)
        if not positions:
            return self._result("NO_MATCH", response=response)
        if len(positions) > 1:
            return self._result("AMBIGUOUS", response=response, candidate_count=len(positions))
        return self._result(
            "OK",
            response=response,
            candidate_count=1,
            position=positions[0],
        )

    @staticmethod
    def _parse_candidates(payload: object, request: GeocodeRequest):
        if not isinstance(payload, list) or len(payload) > 5:
            return None

        bounds = request.bounds
        positions = []
        for candidate in payload:
            if not isinstance(candidate, dict):
                return None
            latitude = _coordinate(candidate.get("lat"))
            longitude = _coordinate(candidate.get("lon"))
            if latitude is None or longitude is None:
                return None
            try:
                in_range = (
                    Decimal("-90") <= latitude <= Decimal("90") and
                    Decimal("-180") <= longitude <= Decimal("180")
                )
                in_request_bounds = (
                    Decimal(str(bounds.south)) <= latitude <= Decimal(str(bounds.north)) and
                    Decimal(str(bounds.west)) <= longitude <= Decimal(str(bounds.east))
                )
            except InvalidOperation:
                return None
            latitude_float, longitude_float = float(latitude), float(longitude)
            if (not in_range or not in_request_bounds or
                    not math.isfinite(latitude_float) or not math.isfinite(longitude_float)):
                return None

            positions.append(Position(
                lat=latitude_float,
                lng=longitude_float,
                precision="APPROXIMATE",
                source=_GEOCODER,
            ))
        return positions

    def _result(
        self,
        status: str,
        *,
        response: ProviderResponse | None = None,
        candidate_count: int = 0,
        position=None,
    ) -> GeocodeResult:
        policy = self._settings.provider_policies.get(_GEOCODER)
        attribution = list(policy.attribution) if response is not None and policy is not None else []
        return GeocodeResult(
            provider=_GEOCODER,
            status=status,
            position=position,
            candidate_count=candidate_count,
            queried_at=None if response is None else response.observed_at,
            evidence_kind="NONE" if response is None else response.evidence_kind,
            attribution=attribution,
        )


def _coordinate(value: object) -> Decimal | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        number = Decimal(value.strip())
    except (InvalidOperation, ValueError):
        return None
    return number if number.is_finite() else None


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON object key")
        result[key] = value
    return result


def _reject_json_constant(value: str):
    raise ValueError("non-standard JSON numeric constant")
