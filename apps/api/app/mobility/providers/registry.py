"""Safe provider selection for the new mobility lane."""
import importlib

from ..contracts import (
    GeocodeRequest,
    GeocodeResult,
    NearbyResult,
    ResolvedNearbyRequest,
    ResolvedRouteRequest,
    RouteResult,
)
from .base import GeocoderProvider, PlacesProvider, RouteProvider
from .open_config import OpenMobilitySettings


class DisabledRouteProvider:
    def __init__(self, provider: str = "none", status: str = "NOT_CONFIGURED"):
        self._provider = provider
        self._status = status

    async def compute_route(self, request: ResolvedRouteRequest) -> RouteResult:
        return RouteResult(
            listing_id=request.request.listing_id,
            campus_id=request.request.campus_id,
            provider=self._provider,
            requested_mode=request.request.requested_mode,
            status=self._status,
            coordinate_version=request.destination.coordinate_version,
        )


class DisabledPlacesProvider:
    def __init__(self, provider: str = "none", status: str = "NOT_CONFIGURED"):
        self._provider = provider
        self._status = status

    async def nearby(self, request: ResolvedNearbyRequest) -> NearbyResult:
        return NearbyResult(
            listing_id=request.request.listing_id,
            radius_m=request.request.radius_m,
            categories=request.request.categories,
            provider=self._provider,
            status=self._status,
        )


class DisabledGeocoderProvider:
    def __init__(self, provider: str = "none", status: str = "NOT_CONFIGURED"):
        self._provider = provider
        self._status = status

    async def geocode(self, request: GeocodeRequest) -> GeocodeResult:
        return GeocodeResult(
            provider=self._provider,
            status=self._status,
            candidate_count=0,
        )


def build_route_provider(settings: OpenMobilitySettings | None) -> RouteProvider:
    settings = settings or OpenMobilitySettings()
    name = settings.routing_provider
    if name == "disabled":
        return DisabledRouteProvider()
    adapter = _load_adapter("ors_routes", "ORSRouteProvider")
    if adapter is None:
        return DisabledRouteProvider(name, "CAPABILITY_UNVERIFIED")
    # The adapter resolves mode capability before checking its configuration.
    return adapter(settings)


def build_places_provider(settings: OpenMobilitySettings | None) -> PlacesProvider:
    settings = settings or OpenMobilitySettings()
    name = settings.places_provider
    if name == "disabled":
        return DisabledPlacesProvider()
    adapter = _load_adapter("overpass_places", "OverpassPlacesProvider")
    if adapter is None:
        return DisabledPlacesProvider(name, "CAPABILITY_UNVERIFIED")
    if not settings.enabled or not settings.live_enabled or not settings.overpass_url:
        return DisabledPlacesProvider(name, "NOT_CONFIGURED")
    return adapter(settings)


def build_geocoder_provider(settings: OpenMobilitySettings | None) -> GeocoderProvider:
    settings = settings or OpenMobilitySettings()
    name = settings.geocoder_provider
    if name == "disabled":
        return DisabledGeocoderProvider()
    adapter = _load_adapter("nominatim_geocoder", "NominatimGeocoder")
    if adapter is None:
        return DisabledGeocoderProvider(name, "CAPABILITY_UNVERIFIED")
    if not settings.enabled or not settings.live_enabled or not settings.nominatim_url:
        return DisabledGeocoderProvider(name, "NOT_CONFIGURED")
    return adapter(settings)


def _load_adapter(module_name: str, class_name: str):
    qualified_name = f"{__package__}.{module_name}"
    try:
        module = importlib.import_module(f".{module_name}", __package__)
    except ModuleNotFoundError as exc:
        if exc.name == qualified_name:
            return None
        raise
    return getattr(module, class_name)
