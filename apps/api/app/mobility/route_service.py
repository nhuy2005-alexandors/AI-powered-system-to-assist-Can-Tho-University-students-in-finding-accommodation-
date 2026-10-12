"""Resolve route endpoints from the read-only catalog before invoking a provider."""
from typing import Any

from .campuses import get_campus
from .contracts import (CatalogListing, ResolvedRouteRequest, RouteRequest,
                        RouteResult)
from .providers.base import RouteProvider
from .warnings import build_warnings


class RouteService:
    def __init__(self, catalog: Any, provider: RouteProvider):
        self._catalog = catalog
        self._provider = provider

    async def route(self, request: RouteRequest) -> RouteResult:
        listing: CatalogListing | None = self._catalog.get_listing(request.listing_id)
        if listing is None:
            raise LookupError("listing not found")

        campus = get_campus(request.campus_id)
        if listing.position is None:
            result = RouteResult(
                listing_id=request.listing_id,
                campus_id=request.campus_id,
                requested_mode=request.requested_mode,
                status="LOCATION_UNAVAILABLE",
                coordinate_version=campus.coordinate_version,
            )
        else:
            resolved = ResolvedRouteRequest(
                request=request,
                origin=listing.position,
                destination=campus,
            )
            result = await self._provider.compute_route(resolved)

        return result.model_copy(update={"warnings": build_warnings(listing, result)})
