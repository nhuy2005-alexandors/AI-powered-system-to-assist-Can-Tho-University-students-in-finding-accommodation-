"""Feature-gated internal mobility endpoints with server-resolved coordinates."""
from typing import Any
import re

from fastapi import APIRouter, FastAPI, HTTPException, Query

from .campuses import CAMPUSES
from .contracts import (BoundingBox, CatalogPage, Campus, GeocodeRequest, GeocodeResult, NearbyRequest, NearbyResult,
                        RouteRequest, RouteResult)
from .providers.base import MobilitySettings, PlacesProvider, RouteProvider
from .providers.open_config import OpenMobilitySettings
from .providers.registry import build_geocoder_provider, build_places_provider, build_route_provider


def install_mobility(app: FastAPI, *, catalog: Any = None, enabled: bool = False,
                     config: MobilitySettings | None = None,
                     open_settings: OpenMobilitySettings | None = None,
                     demo_geocode_enabled: bool = False,
                     route_provider: RouteProvider | None = None,
                     places_provider: PlacesProvider | None = None) -> None:
    if not enabled:
        return
    from .catalog_repo import CatalogUnavailable
    from .place_service import PlaceService
    from .route_service import RouteService

    app.state.mobility_catalog = catalog
    # The legacy Google-shaped test seam never selects a new production provider.
    # Only the separate open settings and registry may select the mobility backend.
    open_settings = open_settings or OpenMobilitySettings()
    routes = route_provider or build_route_provider(open_settings)
    places = places_provider or build_places_provider(open_settings)
    router = APIRouter(prefix="/mobility", tags=["mobility"])

    def current_catalog():
        if app.state.mobility_catalog is None:
            raise HTTPException(503, "DATASET_NOT_READY")
        return app.state.mobility_catalog

    @router.get("/campuses", response_model=list[Campus])
    def campuses():
        return CAMPUSES

    @router.get("/listings", response_model=CatalogPage)
    def listings(page: int = Query(1, ge=1), size: int = Query(50, ge=1, le=100),
                 south: float | None = Query(None, ge=-90, le=90),
                 north: float | None = Query(None, ge=-90, le=90),
                 west: float | None = Query(None, ge=-180, le=180),
                 east: float | None = Query(None, ge=-180, le=180)):
        extents = [south, north, west, east]
        if any(value is not None for value in extents) and not all(value is not None for value in extents):
            raise HTTPException(422, "bbox requires south/north/west/east")
        bbox = None
        if all(value is not None for value in extents):
            try:
                bbox = BoundingBox(south=south, north=north, west=west, east=east)
            except ValueError:
                raise HTTPException(422, "invalid bbox") from None
        try:
            return current_catalog().list_page(page=page, size=size, bbox=bbox)
        except CatalogUnavailable:
            raise HTTPException(503, "DATASET_NOT_READY") from None

    @router.post("/routes", response_model=RouteResult)
    async def route(request: RouteRequest):
        try:
            return await RouteService(current_catalog(), routes).route(request)
        except CatalogUnavailable:
            raise HTTPException(503, "DATASET_NOT_READY") from None
        except LookupError:
            raise HTTPException(404, "LISTING_NOT_FOUND") from None

    @router.post("/nearby", response_model=NearbyResult)
    async def nearby(request: NearbyRequest):
        try:
            return await PlaceService(current_catalog(), places).nearby(request)
        except CatalogUnavailable:
            raise HTTPException(503, "DATASET_NOT_READY") from None
        except LookupError:
            raise HTTPException(404, "LISTING_NOT_FOUND") from None

    # Production callers do not opt in. This is explicit interactive demo only.
    if demo_geocode_enabled:
        geocoder = build_geocoder_provider(open_settings)

        @router.post("/geocode", response_model=GeocodeResult)
        async def geocode(request: GeocodeRequest):
            if ("@" in request.address or
                    re.search(r"(?:\d[\s().+\-]*){9,}", request.address)):
                raise HTTPException(422, "PUBLIC_PLACE_ONLY")
            return await geocoder.geocode(request)

    app.include_router(router)
