import type {
  CatalogListing,
  NearbyResult,
  RouteResult,
} from "./mobility-contracts";

export type MapConfig = {
  enabled: boolean;
  tileUrl: string | null;
  attribution: string;
  allowedTileOrigin: string | null;
};

export interface MapProvider {
  setListings(listings: CatalogListing[]): void;
  setSelection(id: number | null): void;
  setRoute(route: RouteResult | null): void;
  setPlaces(places: NearbyResult | null): void;
  destroy(): void;
}

export type LeafletProviderFactory = (
  element: HTMLElement,
  config: MapConfig,
  onSelect: (id: number) => void,
) => MapProvider;

const unavailableProvider: MapProvider = {
  setListings: () => undefined,
  setSelection: () => undefined,
  setRoute: () => undefined,
  setPlaces: () => undefined,
  destroy: () => undefined,
};

export function createLeafletProvider(
  _element: HTMLElement,
  config: MapConfig,
  _onSelect: (id: number) => void,
): MapProvider {
  if (!config.enabled || !config.tileUrl || !config.allowedTileOrigin) {
    return unavailableProvider;
  }
  if (typeof window === "undefined") {
    return unavailableProvider;
  }
  try {
    const tile = new URL(config.tileUrl);
    if (tile.protocol !== "https:" || tile.origin !== config.allowedTileOrigin) {
      return unavailableProvider;
    }
  } catch {
    return unavailableProvider;
  }

  // The Leaflet renderer is added by the UI lane; this P0 contract performs no I/O.
  return unavailableProvider;
}
