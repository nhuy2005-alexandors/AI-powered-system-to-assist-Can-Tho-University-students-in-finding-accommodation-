"""Foundation never permits real Google traffic, even with an accidental key."""
from typing import Protocol

import httpx
from pydantic import BaseModel, ConfigDict, Field, SecretStr

from ..contracts import (GeocodeRequest, GeocodeResult, NearbyResult, PlaceCategory,
                         ResolvedNearbyRequest, ResolvedRouteRequest, RouteResult, TravelMode)


class MobilitySettings(BaseModel):
    model_config = ConfigDict(extra="forbid")
    enabled: bool = False
    live_enabled: bool = False
    server_api_key: SecretStr = SecretStr("")
    timeout_seconds: float = Field(default=10.0, gt=0, le=30, allow_inf_nan=False)
    region: str = "VN"
    allowed_modes: set[TravelMode] = Field(default_factory=set)
    allowed_categories: set[PlaceCategory] = Field(default_factory=set)


def request_gate(config: MobilitySettings, capability: str,
                 transport: httpx.AsyncBaseTransport | None, *, nearby: bool = False) -> str | None:
    if not config.enabled or not config.live_enabled or not config.server_api_key.get_secret_value():
        return "NOT_CONFIGURED"
    allowed = config.allowed_categories if nearby else config.allowed_modes
    if capability not in allowed:
        return "CAPABILITY_UNVERIFIED"
    # No production fixture switch. Tests inject MockTransport directly; all real
    # transports stay barred until a separately approved live operation.
    if not isinstance(transport, httpx.MockTransport):
        return "CAPABILITY_UNVERIFIED"
    return None


class RouteProvider(Protocol):
    async def compute_route(self, request: ResolvedRouteRequest) -> RouteResult: ...


class PlacesProvider(Protocol):
    async def nearby(self, request: ResolvedNearbyRequest) -> NearbyResult: ...


class GeocoderProvider(Protocol):
    async def geocode(self, request: GeocodeRequest) -> GeocodeResult: ...
