import type {
  CircleMarker,
  FeatureGroup,
  Layer,
  Marker,
  Map as LeafletMap,
  Polyline,
} from "leaflet";
import {
  createCampusIcon,
  createHousingIcon,
  focusSelectedPosition,
  observeMapResize,
  scrollMapSelection,
} from "../../lib/map-ui";
import type {
  Campus,
  CatalogListing,
  NearbyResult,
  Place,
  Position,
  RouteResult,
} from "@/lib/mobility-contracts";
import type { MapConfig, MapProvider } from "@/lib/map-provider";

export type LeafletUiProvider = MapProvider & {
  setCampuses(campuses: Campus[]): void;
  getListingLayerSnapshot(): ListingLayerSnapshot;
};

export type ListingLayerSnapshot = {
  generation: number;
  state: "READY" | "UNAVAILABLE";
  members: readonly { id: number; lat: number; lng: number }[];
};

type ListingMarker = Marker & { readonly listingId: number };

export type CatalogClusterGroup = FeatureGroup & {
  addLayers(layers: Marker[]): CatalogClusterGroup;
  zoomToShowLayer(layer: Marker, callback?: () => void): void;
  getVisibleParent(layer: Marker): Layer | null;
};

type MarkerClusterOptions = {
  chunkedLoading: false;
  animate: false;
  animateAddingMarkers: false;
};

type LeafletWithMarkerCluster = typeof import("leaflet") & {
  MarkerClusterGroup?: new (options: MarkerClusterOptions) => CatalogClusterGroup;
};

const ROUTE_PROFILES: Record<string, string> = {
  WALK: "foot-walking",
  BICYCLE: "cycling-regular",
};

function validPosition(value: Position | null | undefined): value is Position {
  return (
    value != null &&
    Number.isFinite(value.lat) &&
    Number.isFinite(value.lng) &&
    value.lat >= -90 &&
    value.lat <= 90 &&
    value.lng >= -180 &&
    value.lng <= 180
  );
}

function unavailableListingSnapshot(generation: number): ListingLayerSnapshot {
  return Object.freeze({
    generation,
    state: "UNAVAILABLE",
    members: Object.freeze([]),
  });
}

export function readListingLayerSnapshot(
  group: CatalogClusterGroup | null,
  generation: number,
  markerClass: typeof import("leaflet").Marker | null,
): ListingLayerSnapshot {
  if (!group || !markerClass) return unavailableListingSnapshot(generation);

  try {
    const layers = group.getLayers();
    if (!Array.isArray(layers)) return unavailableListingSnapshot(generation);

    const members: Array<{ id: number; lat: number; lng: number }> = [];
    for (const layer of layers) {
      if (!(layer instanceof markerClass)) return unavailableListingSnapshot(generation);
      const marker = layer as ListingMarker;
      const idDescriptor = Object.getOwnPropertyDescriptor(marker, "listingId");
      if (
        !idDescriptor ||
        idDescriptor.writable !== false ||
        !Number.isSafeInteger(marker.listingId) ||
        marker.listingId <= 0
      ) {
        return unavailableListingSnapshot(generation);
      }

      const position = marker.getLatLng();
      if (
        !Number.isFinite(position.lat) ||
        !Number.isFinite(position.lng) ||
        position.lat < -90 ||
        position.lat > 90 ||
        position.lng < -180 ||
        position.lng > 180
      ) {
        return unavailableListingSnapshot(generation);
      }
      members.push({ id: marker.listingId, lat: position.lat, lng: position.lng });
    }

    members.sort((left, right) => left.id - right.id);
    return Object.freeze({
      generation,
      state: "READY",
      members: Object.freeze(members.map((member) => Object.freeze(member))),
    });
  } catch {
    return unavailableListingSnapshot(generation);
  }
}

function validCampus(value: Campus | null | undefined): value is Campus {
  return (
    value != null &&
    Number.isFinite(value.lat) &&
    Number.isFinite(value.lng) &&
    value.lat >= -90 &&
    value.lat <= 90 &&
    value.lng >= -180 &&
    value.lng <= 180 &&
    typeof value.name === "string"
  );
}

function validObservedAt(value: string | null | undefined): value is string {
  if (typeof value !== "string") return false;
  const timestamp = value.trim();
  const match = timestamp.match(
    /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$/i,
  );
  if (!match) return false;

  const [, year, month, day, hour, minute, second] = match;
  const numericYear = Number(year);
  const numericMonth = Number(month);
  const numericDay = Number(day);
  const calendarDate = new Date(`${year}-${month}-${day}T00:00:00.000Z`);
  return (
    Number.isFinite(Date.parse(timestamp)) &&
    Number.isFinite(calendarDate.getTime()) &&
    calendarDate.getUTCFullYear() === numericYear &&
    calendarDate.getUTCMonth() === numericMonth - 1 &&
    calendarDate.getUTCDate() === numericDay &&
    Number(hour) <= 23 &&
    Number(minute) <= 59 &&
    Number(second) <= 59
  );
}

function validRoutePosition(value: Position): boolean {
  return (
    validPosition(value) &&
    (value.source === null ||
      (typeof value.source === "string" && !value.source.toLowerCase().includes("google")))
  );
}

function validTileConfig(config: MapConfig): config is MapConfig & {
  tileUrl: string;
  allowedTileOrigin: string;
} {
  if (!config.enabled || !config.tileUrl || !config.allowedTileOrigin || !config.attribution.trim()) {
    return false;
  }
  try {
    const tile = new URL(config.tileUrl);
    const origin = new URL(config.allowedTileOrigin);
    return (
      tile.protocol === "https:" &&
      origin.protocol === "https:" &&
      !tile.username &&
      !tile.password &&
      !tile.search &&
      !tile.hash &&
      tile.origin === origin.origin &&
      (origin.pathname === "/" || origin.pathname === "") &&
      !origin.username &&
      !origin.password &&
      !origin.search &&
      !origin.hash
    );
  } catch {
    return false;
  }
}

function escapeAttributionText(value: string): string {
  return value.replace(/[&<>"']/g, (character) => {
    const escaped: Record<string, string> = {
      "&": "&amp;",
      "<": "&lt;",
      ">": "&gt;",
      '"': "&quot;",
      "'": "&#39;",
    };
    return escaped[character];
  });
}

function safePopup(
  document: Document,
  title: string,
  description: string,
): HTMLElement {
  const content = document.createElement("div");
  const heading = document.createElement("strong");
  heading.textContent = title;
  const note = document.createElement("p");
  note.textContent = description;
  note.className = "mt-1 text-xs";
  content.append(heading, note);
  return content;
}

function safeHttpSourceUrl(value: string | null): string | null {
  if (!value) return null;
  try {
    const url = new URL(value.trim());
    if (
      (url.protocol !== "http:" && url.protocol !== "https:") ||
      url.username.length > 0 ||
      url.password.length > 0
    ) return null;
    return url.href;
  } catch {
    return null;
  }
}

function safeListingPopup(
  document: Document,
  listing: CatalogListing,
  position: Position,
): HTMLElement {
  const content = document.createElement("div");
  const heading = document.createElement("strong");
  heading.textContent = listing.title;
  const price = document.createElement("p");
  price.className = "font-semibold text-emerald-700";
  price.textContent = listing.price === null || !Number.isFinite(listing.price)
    ? "Giá chưa rõ"
    : `${new Intl.NumberFormat("vi-VN").format(listing.price)} đ/tháng`;
  const address = document.createElement("p");
  address.className = "text-sm text-slate-600";
  address.textContent = listing.address?.trim() || "Địa chỉ chưa rõ";
  const precision = position.precision === "APPROXIMATE"
    ? "Vị trí gần đúng; cần xác nhận địa điểm và lối vào."
    : position.precision === "VERIFIED"
      ? "Vị trí có nguồn xác minh."
      : "Độ chính xác vị trí chưa rõ.";
  const provenance = position.source?.trim()
    ? ` Nguồn tọa độ: ${position.source}.`
    : " Nguồn tọa độ chưa rõ.";
  const note = document.createElement("p");
  note.className = "mt-1 text-xs";
  note.textContent = `${precision}${provenance}`;
  content.append(heading, price, address, note);

  const sourceUrl = safeHttpSourceUrl(listing.source_url);
  if (sourceUrl) {
    const sourceLink = document.createElement("a");
    sourceLink.href = sourceUrl;
    sourceLink.target = "_blank";
    sourceLink.rel = "noopener noreferrer";
    sourceLink.className = "mt-1 inline-block text-sm text-blue-700 underline";
    sourceLink.textContent = "Xem tin gốc";
    content.append(sourceLink);
  }
  return content;
}

export function routeCanRender(value: RouteResult | null | undefined): value is RouteResult {
  return (
    value != null &&
    typeof value.provider === "string" &&
    value.provider.toLowerCase() === "ors" &&
    value.status === "OK" &&
    (value.evidence_kind === "LIVE" || value.evidence_kind === "SYNTHETIC_FIXTURE") &&
    validObservedAt(value.observed_at) &&
    (value.requested_mode === "WALK" || value.requested_mode === "BICYCLE") &&
    value.effective_mode === value.requested_mode &&
    value.provider_profile === ROUTE_PROFILES[value.requested_mode] &&
    Array.isArray(value.attribution) &&
    value.attribution.length > 0 &&
    value.attribution.every((entry) => typeof entry === "string" && entry.trim().length > 0) &&
    Array.isArray(value.polyline) &&
    value.polyline.length >= 2 &&
    value.polyline.every(validRoutePosition)
  );
}

function placeCanRender(value: Place): boolean {
  return (
    value != null &&
    Number.isFinite(value.lat) &&
    Number.isFinite(value.lng) &&
    value.lat >= -90 &&
    value.lat <= 90 &&
    value.lng >= -180 &&
    value.lng <= 180 &&
    typeof value.provider_place_id === "string" &&
    typeof value.name === "string" &&
    value.name.trim().length > 0 &&
    Array.isArray(value.attribution) &&
    value.attribution.length > 0 &&
    value.attribution.every((entry) => typeof entry === "string" && entry.trim().length > 0)
  );
}

export function placesCanRender(value: NearbyResult | null | undefined): value is NearbyResult {
  return (
    value != null &&
    typeof value.provider === "string" &&
    value.provider.toLowerCase() === "osm_overpass" &&
    value.status === "OK" &&
    (value.evidence_kind === "LIVE" || value.evidence_kind === "SYNTHETIC_FIXTURE") &&
    typeof value.queried_at === "string" &&
    value.queried_at.length > 0 &&
    Array.isArray(value.items) &&
    value.items.every(placeCanRender)
  );
}

export function createLeafletProvider(
  element: HTMLElement,
  config: MapConfig,
  onSelect: (id: number) => void,
): LeafletUiProvider {
  let destroyed = false;
  let initGeneration = 0;
  let map: LeafletMap | null = null;
  let leafletInstance: typeof import("leaflet") | null = null;
  let markerClass: typeof import("leaflet").Marker | null = null;
  let listingLayer: CatalogClusterGroup | null = null;
  let selectionLayer: FeatureGroup | null = null;
  let campusLayer: FeatureGroup | null = null;
  let routeLayer: FeatureGroup | null = null;
  let placesLayer: FeatureGroup | null = null;
  let resizeCleanup: (() => void) | null = null;
  let listings: CatalogListing[] = [];
  let campuses: Campus[] = [];
  let selectedId: number | null = null;
  let listingGeneration = 0;
  const listingMarkers = new Map<number, ListingMarker>();
  let route: RouteResult | null = null;
  let places: NearbyResult | null = null;
  let tileBatchStarted = false;
  let tileBatchHasError = false;
  let hasFittedInitialBounds = false;
  let tileAttached = false;

  const setTileStatus = (status: "disabled" | "loading" | "ready" | "error") => {
    element.dataset.tileStatus = status;
  };

  const cancelSelectionMotion = () => map?.stop();

  const refreshLayer = (render: (leaflet: typeof import("leaflet")) => void, fitBounds = false) => {
    if (destroyed || !map || !leafletInstance) return;
    render(leafletInstance);
    if (fitBounds) fitInitialBounds(leafletInstance);
  };

  function markPath<T extends CircleMarker | Polyline>(
    layer: T,
    attributes: Record<string, string>,
  ): void {
    const applyAttributes = () => {
      const node = layer.getElement();
      if (!node) return;
      for (const [name, value] of Object.entries(attributes)) node.setAttribute(name, value);
    };
    layer.on("add", applyAttributes);
    applyAttributes();
  }

  function markMarker(marker: Marker, attributes: Record<string, string>): void {
    const applyAttributes = () => {
      const node = marker.getElement();
      if (!node) return;
      for (const [name, value] of Object.entries(attributes)) node.setAttribute(name, value);
    };
    marker.on("add", applyAttributes);
    applyAttributes();
  }

  function bindListingSelection(marker: Marker, id: number): void {
    marker.on("click", () => onSelect(id));
    marker.on("keydown", (event) => {
      if (event.originalEvent.key !== "Enter") return;
      event.originalEvent.preventDefault();
      onSelect(id);
    });
  }

  function renderListingLayer(leaflet: typeof import("leaflet")) {
    if (destroyed || !map || !listingLayer) return;
    listingLayer.clearLayers();
    listingMarkers.clear();
    const markers: ListingMarker[] = [];
    for (const listing of listings) {
      const position = listing.position;
      if (!position || !validPosition(position)) continue;
      const marker = leaflet.marker([position.lat, position.lng], {
        icon: createHousingIcon(leaflet, false),
        keyboard: true,
        riseOnHover: true,
      });
      Object.defineProperty(marker, "listingId", {
        value: listing.id,
        enumerable: true,
        writable: false,
        configurable: false,
      });
      const listingMarker = marker as ListingMarker;
      listingMarkers.set(listing.id, listingMarker);
      markMarker(listingMarker, {
        "data-listing-pin-id": String(listing.id),
        "data-precision": position.precision,
        "aria-label": listing.title,
        role: "button",
        tabindex: "0",
      });
      bindListingSelection(marker, listing.id);
      marker.bindPopup(safeListingPopup(element.ownerDocument, listing, position), {
        autoPan: false, maxHeight: 90, maxWidth: 260,
      });
      markers.push(listingMarker);
    }
    listingLayer.addLayers(markers);
  }

  function focusSelectedListing(id: number): void {
    if (destroyed || !map || !leafletInstance || selectedId !== id) return;
    const position = listings.find((listing) => listing.id === id)?.position;
    if (!position || !validPosition(position)) return;
    renderSelectedOverlay(id, leafletInstance);
    focusSelectedPosition(map, [position.lat, position.lng]);
  }

  function renderSelectedOverlay(id: number, leaflet: typeof import("leaflet")): void {
    if (destroyed || !map || !selectionLayer) return;
    const listing = listings.find((candidate) => candidate.id === id);
    const position = listing?.position;
    if (!listing || !position || !validPosition(position)) return;

    // This independent marker presents the selection; it is never part of the catalog cluster snapshot.
    selectionLayer.clearLayers();
    const overlay = leaflet.marker([position.lat, position.lng], {
      icon: createHousingIcon(leaflet, true),
      keyboard: true,
      riseOnHover: true,
      zIndexOffset: 10_000,
    });
    markMarker(overlay, {
      "data-selection-overlay-id": String(id),
      "data-lat": String(position.lat),
      "data-lng": String(position.lng),
      "aria-label": `Tin được chọn: ${listing.title}`,
      role: "button",
      tabindex: "0",
    });
    bindListingSelection(overlay, id);
    overlay.bindPopup(safeListingPopup(element.ownerDocument, listing, position), {
      autoPan: false, maxHeight: 90, maxWidth: 260,
    });
    selectionLayer.addLayer(overlay);
    overlay.openPopup();
  }

  function renderCampusLayer(leaflet: typeof import("leaflet")) {
    if (destroyed || !map || !campusLayer) return;
    campusLayer.clearLayers();
    for (const campus of campuses) {
      if (!validCampus(campus)) continue;
      const marker = leaflet.marker([campus.lat, campus.lng], {
        icon: createCampusIcon(leaflet),
        keyboard: true,
      });
      markMarker(marker, {
        "data-campus-id": campus.id,
        "data-lat": String(campus.lat),
        "data-lng": String(campus.lng),
        "data-verification": campus.verification_status,
      });
      const label = element.ownerDocument.createElement("span");
      label.textContent = campus.verification_status === "PROVISIONAL"
        ? `${campus.name} · vị trí tạm thời`
        : campus.name;
      marker.bindTooltip(label, { permanent: true, direction: "right", offset: [9, 0] });
      campusLayer.addLayer(marker);
    }
  }

  function renderRouteLayer(leaflet: typeof import("leaflet")) {
    if (destroyed || !map || !routeLayer) return;
    routeLayer.clearLayers();
    const routeToRender = route;
    const routeGeometry = routeToRender?.polyline;
    if (routeCanRender(routeToRender) && routeGeometry) {
      const line = leaflet.polyline(
        routeGeometry.map((point) => [point.lat, point.lng]),
        {
          color: "#7c3aed",
          weight: 5,
          opacity: 0.9,
          dashArray: routeToRender.evidence_kind === "SYNTHETIC_FIXTURE" ? "8 8" : undefined,
        },
      );
      markPath(line, {
        "data-route-source": routeToRender.evidence_kind,
        "data-route-provider": "ors",
      });
      routeLayer.addLayer(line);
    }
  }

  function renderPlacesLayer(leaflet: typeof import("leaflet")) {
    if (destroyed || !map || !placesLayer) return;
    placesLayer.clearLayers();
    if (places && placesCanRender(places)) {
      for (const place of places.items) {
        const marker = leaflet.circleMarker([place.lat, place.lng], {
          radius: 5,
          color: "#ffffff",
          weight: 2,
          fillColor: "#d97706",
          fillOpacity: 0.96,
        });
        markPath(marker, {
          "data-nearby-place-id": place.provider_place_id,
          "data-nearby-source": places.evidence_kind,
        });
        marker.bindPopup(
          safePopup(
            element.ownerDocument,
            place.name,
            "Tiện ích từ dữ liệu OpenStreetMap; vị trí cần được xác nhận.",
          ),
        );
        placesLayer.addLayer(marker);
      }
    }
  }

  function fitInitialBounds(leaflet: typeof import("leaflet")) {
    if (destroyed || !map || hasFittedInitialBounds || listings.length === 0 || campuses.length === 0) return;
    const bounds: [number, number][] = [
      ...listings.flatMap((listing) =>
        listing.position && validPosition(listing.position)
          ? [[listing.position.lat, listing.position.lng] as [number, number]]
          : [],
      ),
      ...campuses.flatMap((campus) =>
        validCampus(campus) ? [[campus.lat, campus.lng] as [number, number]] : [],
      ),
    ];
    if (bounds.length > 0) {
      map.fitBounds(leaflet.latLngBounds(bounds), { padding: [24, 24], maxZoom: 15, animate: false });
      hasFittedInitialBounds = true;
      const extents = map.getBounds();
      element.dataset.initialFitZoom = String(map.getZoom());
      element.dataset.initialFitSouth = String(extents.getSouth());
      element.dataset.initialFitNorth = String(extents.getNorth());
      element.dataset.initialFitWest = String(extents.getWest());
      element.dataset.initialFitEast = String(extents.getEast());
      attachTileLayer(leaflet);
    }
  }

  function attachTileLayer(leaflet: typeof import("leaflet")) {
    if (destroyed || !map || !hasFittedInitialBounds || tileAttached || !validTileConfig(config)) return;
    tileAttached = true;
    element.dataset.tileWaitingForCatalog = "false";
    const tileLayer = leaflet.tileLayer(config.tileUrl, {
      attribution: escapeAttributionText(config.attribution), maxZoom: 19,
      crossOrigin: false, updateWhenZooming: false, updateWhenIdle: true, keepBuffer: 0,
    });
    tileLayer.on("loading", () => {
      if (destroyed) return;
      tileBatchStarted = true;
      tileBatchHasError = false;
      setTileStatus("loading");
    });
    tileLayer.on("tileerror", () => {
      if (destroyed || !tileBatchStarted) return;
      tileBatchHasError = true;
    });
    tileLayer.on("load", () => {
      if (destroyed || !tileBatchStarted) return;
      setTileStatus(tileBatchHasError ? "error" : "ready");
    });
    tileLayer.addTo(map);
  }

  function renderLayers(leaflet: typeof import("leaflet")) {
    renderListingLayer(leaflet);
    renderCampusLayer(leaflet);
    renderRouteLayer(leaflet);
    renderPlacesLayer(leaflet);
    fitInitialBounds(leaflet);
    if (selectedId !== null) focusSelectedListing(selectedId);
  }

  element.dataset.tileWaitingForCatalog = validTileConfig(config) ? "true" : "false";
  for (const key of ["initialFitZoom", "initialFitSouth", "initialFitNorth", "initialFitWest", "initialFitEast"]) {
    delete element.dataset[key];
  }
  setTileStatus("disabled");
  if (!element.isConnected) setTileStatus("disabled");

  if (typeof window !== "undefined" && element.isConnected) {
    const currentInitGeneration = initGeneration;
    void import("leaflet")
      .then(async (module) => {
        await import("leaflet.markercluster");
        if (
          destroyed ||
          initGeneration !== currentInitGeneration ||
          !element.isConnected
        ) return;
        const leaflet = module.default;
        const clusterConstructor = (leaflet as LeafletWithMarkerCluster).MarkerClusterGroup;
        if (typeof clusterConstructor !== "function") {
          throw new Error("leaflet.markercluster 1.5.3 did not register MarkerClusterGroup");
        }
        leafletInstance = leaflet;
        markerClass = leaflet.Marker;
        map = leaflet.map(element, {
          zoomControl: true,
          attributionControl: true,
          preferCanvas: false,
          maxZoom: 19,
        });
        const firstCampus = campuses.find(validCampus);
        const firstListing = listings.find((listing) => listing.position && validPosition(listing.position));
        const center = firstCampus
          ? [firstCampus.lat, firstCampus.lng] as [number, number]
          : firstListing?.position
            ? [firstListing.position.lat, firstListing.position.lng] as [number, number]
            : [10.0322, 105.7683] as [number, number];
        map.setView(center, 13);
        listingLayer = new clusterConstructor({
          chunkedLoading: false,
          animate: false,
          animateAddingMarkers: false,
        }).addTo(map);
        selectionLayer = leaflet.featureGroup().addTo(map);
        campusLayer = leaflet.featureGroup().addTo(map);
        routeLayer = leaflet.featureGroup().addTo(map);
        placesLayer = leaflet.featureGroup().addTo(map);
        resizeCleanup = observeMapResize(map);

        renderLayers(leaflet);
      })
      .catch(() => {
        if (!destroyed && initGeneration === currentInitGeneration) {
          setTileStatus(config.enabled ? "error" : "disabled");
        }
      });
  }

  return {
    setListings(value) {
      cancelSelectionMotion();
      selectionLayer?.clearLayers();
      listings = value;
      listingGeneration += 1;
      refreshLayer(renderListingLayer, true);
      if (selectedId !== null && leafletInstance) renderSelectedOverlay(selectedId, leafletInstance);
    },
    setCampuses(value) {
      campuses = value;
      refreshLayer(renderCampusLayer, true);
    },
    getListingLayerSnapshot() {
      return readListingLayerSnapshot(
        destroyed ? null : listingLayer,
        listingGeneration,
        destroyed ? null : markerClass,
      );
    },
    setSelection(id) {
      cancelSelectionMotion();
      selectionLayer?.clearLayers();
      selectedId = id;
      const leaflet = leafletInstance;
      if (!leaflet || destroyed || !map || !listingLayer) return;
      if (id !== null) focusSelectedListing(id);
    },
    setRoute(value) {
      route = value;
      refreshLayer(renderRouteLayer);
    },
    setPlaces(value) {
      places = value;
      refreshLayer(renderPlacesLayer);
    },
    destroy() {
      if (destroyed) return;
      destroyed = true;
      cancelSelectionMotion();
      initGeneration += 1;
      listingGeneration += 1;
      resizeCleanup?.();
      resizeCleanup = null;
      listingLayer?.clearLayers();
      selectionLayer?.clearLayers();
      campusLayer?.clearLayers();
      routeLayer?.clearLayers();
      placesLayer?.clearLayers();
      map?.remove();
      listingLayer = null;
      selectionLayer = null;
      listingMarkers.clear();
      campusLayer = null;
      routeLayer = null;
      placesLayer = null;
      map = null;
      leafletInstance = null;
      markerClass = null;
      if (element.isConnected) setTileStatus("disabled");
    },
  };
}
