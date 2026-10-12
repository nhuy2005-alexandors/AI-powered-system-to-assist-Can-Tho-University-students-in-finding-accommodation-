"""Resolve a catalog listing before asking the provider for nearby places."""
from typing import Any

from .contracts import NearbyRequest, NearbyResult, ResolvedNearbyRequest


class PlaceService:
    def __init__(self, catalog: Any, provider: Any):
        self._catalog = catalog
        self._provider = provider

    async def nearby(self, request: NearbyRequest) -> NearbyResult:
        listing = self._catalog.get_listing(request.listing_id)
        if listing is None:
            raise LookupError("listing not found")
        if listing.position is None:
            return NearbyResult(
                listing_id=request.listing_id,
                radius_m=request.radius_m,
                categories=list(request.categories),
                status="LOCATION_UNAVAILABLE",
            )
        return await self._provider.nearby(
            ResolvedNearbyRequest(request=request, center=listing.position)
        )
