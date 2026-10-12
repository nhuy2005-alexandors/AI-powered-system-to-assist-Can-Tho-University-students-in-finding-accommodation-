"use client";

import "leaflet/dist/leaflet.css";
import "leaflet.markercluster/dist/MarkerCluster.css";
import "leaflet.markercluster/dist/MarkerCluster.Default.css";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { Campus, CatalogListing, NearbyResult, RouteResult } from "@/lib/mobility-contracts";
import type { MobilityMapConfig } from "@/lib/config";
import { placesCanRender, routeCanRender } from "./leaflet-map-provider";
import type { LeafletUiProvider, ListingLayerSnapshot } from "./leaflet-map-provider";

type MobilityMapProps = {
  config: MobilityMapConfig;
  campuses: Campus[];
  listings: CatalogListing[];
  selectedListingId: number | null;
  route: RouteResult | null;
  nearby: NearbyResult | null;
  onSelect: (id: number) => void;
};

type TileStatus = "disabled" | "loading" | "ready" | "error";

const UNAVAILABLE_LISTING_SNAPSHOT: ListingLayerSnapshot = Object.freeze({
  generation: 0,
  state: "UNAVAILABLE",
  members: Object.freeze([]),
});

function uniqueAttributions(config: MobilityMapConfig, route: RouteResult | null, nearby: NearbyResult | null): string[] {
  const values = [
    ...(config.enabled ? [config.attribution] : []),
    ...(routeCanRender(route) ? route.attribution : []),
    ...(placesCanRender(nearby) ? nearby.items.flatMap((place) => place.attribution) : []),
  ];
  return [...new Set(values.filter((value) => typeof value === "string" && value.trim().length > 0))];
}

export default function MobilityMap({
  config,
  campuses,
  listings,
  selectedListingId,
  route,
  nearby,
  onSelect,
}: MobilityMapProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const providerRef = useRef<LeafletUiProvider | null>(null);
  const onSelectRef = useRef(onSelect);
  onSelectRef.current = onSelect;
  const stableOnSelect = useCallback((id: number) => onSelectRef.current(id), []);
  const [tileStatus, setTileStatus] = useState<TileStatus>(config.enabled ? "loading" : "disabled");
  const [waitingForCatalog, setWaitingForCatalog] = useState(false);

  const routeKey = JSON.stringify(route);
  const nearbyKey = JSON.stringify(nearby);
  const attributions = useMemo(
    () => uniqueAttributions(config, route, nearby),
    [config, routeKey, nearbyKey],
  );
  const hasSyntheticLayer =
    (routeCanRender(route) && route.evidence_kind === "SYNTHETIC_FIXTURE") ||
    (placesCanRender(nearby) && nearby.evidence_kind === "SYNTHETIC_FIXTURE");
  const hasGooglePayload =
    (typeof route?.provider === "string" && route.provider.toLowerCase() === "google") ||
    (typeof nearby?.provider === "string" && nearby.provider.toLowerCase() === "google");

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const handleSnapshotRequest = (event: Event) => {
      const detail = (event as CustomEvent<{
        respond?: (snapshot: ListingLayerSnapshot) => void;
      }>).detail;
      if (typeof detail?.respond !== "function") return;
      detail.respond(providerRef.current?.getListingLayerSnapshot() ?? UNAVAILABLE_LISTING_SNAPSHOT);
    };
    container.addEventListener("mobility:listing-layer-snapshot", handleSnapshotRequest);
    return () => container.removeEventListener("mobility:listing-layer-snapshot", handleSnapshotRequest);
  }, []);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    let active = true;
    const provider = createProvider(container, config, stableOnSelect);
    providerRef.current = provider;
    provider.setListings(listings);
    provider.setCampuses(campuses);
    provider.setSelection(selectedListingId);
    provider.setRoute(route);
    provider.setPlaces(nearby);

    const observer = new MutationObserver(() => {
      const value = container.dataset.tileStatus;
      if (active && (value === "disabled" || value === "loading" || value === "ready" || value === "error")) {
        setTileStatus(value);
        setWaitingForCatalog(container.dataset.tileWaitingForCatalog === "true");
      }
    });
    observer.observe(container, { attributes: true, attributeFilter: ["data-tile-status", "data-tile-waiting-for-catalog"] });
    setWaitingForCatalog(container.dataset.tileWaitingForCatalog === "true");
    const initialStatus = container.dataset.tileStatus;
    if (initialStatus === "disabled" || initialStatus === "loading" || initialStatus === "ready" || initialStatus === "error") {
      setTileStatus(initialStatus);
    }

    return () => {
      active = false;
      observer.disconnect();
      if (providerRef.current === provider) providerRef.current = null;
      provider.destroy();
    };
    // The map instance belongs to this mounted DOM element. DTO updates use the setter effects below.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [config.enabled, config.tileUrl, config.allowedTileOrigin, config.attribution, stableOnSelect]);

  useEffect(() => {
    providerRef.current?.setListings(listings);
  }, [listings]);

  useEffect(() => {
    providerRef.current?.setCampuses(campuses);
  }, [campuses]);

  useEffect(() => {
    providerRef.current?.setSelection(selectedListingId);
  }, [selectedListingId]);

  useEffect(() => {
    providerRef.current?.setRoute(route);
    // JSON identity keeps the map layer stable through unrelated control changes.
  }, [routeKey]);

  useEffect(() => {
    providerRef.current?.setPlaces(nearby);
    // JSON identity keeps the map layer stable through unrelated control changes.
  }, [nearbyKey]);

  const statusText = tileStatus === "ready"
    ? null
    : tileStatus === "error"
      ? "Bản đồ nền chưa khả dụng; danh sách và chi tiết vẫn hoạt động."
      : tileStatus === "loading"
        ? "Đang tải bản đồ nền; danh sách và chi tiết vẫn hoạt động."
        : waitingForCatalog
          ? "Chờ dữ liệu tọa độ để mở bản đồ nền; danh sách và chi tiết vẫn hoạt động."
          : "Chưa cấu hình bản đồ nền; danh sách và chi tiết vẫn hoạt động.";

  return (
    <section aria-label="Bản đồ tin đăng và khuôn viên" className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
      <div className="flex flex-wrap items-start justify-between gap-3 border-b border-slate-100 px-4 py-3">
        <div>
          <h2 className="font-semibold text-slate-900">Bản đồ di chuyển</h2>
          <p className="mt-1 text-xs text-slate-600">
            Vị trí tin có thể gần đúng; tọa độ và lối vào khuôn viên chưa được xác minh.
          </p>
        </div>
        <div className="flex flex-wrap gap-2 text-xs" aria-label="Chú giải bản đồ">
          <span className="rounded-full bg-rose-50 px-3 py-1 font-medium text-rose-900">Chỗ ở</span>
          <span className="rounded-full bg-blue-50 px-3 py-1 font-medium text-blue-900">Khuôn viên tạm thời</span>
          <span className="rounded-full bg-amber-50 px-3 py-1 font-medium text-amber-900">Tiện ích</span>
        </div>
      </div>
      {statusText && (
        <p
          data-testid="map-tile-status"
          data-status={tileStatus}
          className="border-b border-amber-100 bg-amber-50 px-4 py-2 text-sm text-amber-950"
          role="status"
        >
          {statusText}
        </p>
      )}
      {hasSyntheticLayer && (
        <p
          data-testid="map-provenance"
          className="border-b border-violet-100 bg-violet-50 px-4 py-2 text-sm font-medium text-violet-950"
        >
          Dữ liệu tổng hợp dùng cho thử nghiệm
        </p>
      )}
      {hasGooglePayload && (
        <p
          data-testid="map-google-rejected"
          className="border-b border-amber-100 bg-amber-50 px-4 py-2 text-sm text-amber-950"
        >
          Dữ liệu Google không được hiển thị trên bản đồ.
        </p>
      )}
      <div
        ref={containerRef}
        data-testid="mobility-map"
        data-tile-status={tileStatus}
        className="h-[360px] w-full bg-slate-100"
        role="region"
        aria-label="Bản đồ tương tác"
      />
      <div className="flex flex-wrap gap-x-4 gap-y-1 border-t border-slate-100 px-4 py-2 text-xs text-slate-600">
        <span data-testid="map-attribution">
          {attributions.length > 0 ? attributions.join(" · ") : "Không có tile hoặc attribution provider được cấu hình."}
        </span>
        <span>Tin không có tọa độ vẫn được giữ trong danh sách.</span>
      </div>
    </section>
  );
}

function createProvider(
  element: HTMLElement,
  config: MobilityMapConfig,
  onSelect: (id: number) => void,
): LeafletUiProvider {
  // Leaflet is imported only by the client-only dynamic component and owns the map lifecycle.
  // The P0 provider contract stays unchanged; campuses are a UI-local layer setter.
  const providerPromise = import("./leaflet-map-provider").then(({ createLeafletProvider }) =>
    createLeafletProvider(element, config, onSelect),
  );

  let destroyed = false;
  let campuses: Campus[] = [];
  let listings: CatalogListing[] = [];
  let selectedId: number | null = null;
  let routeValue: RouteResult | null = null;
  let placesValue: NearbyResult | null = null;
  let resolved: LeafletUiProvider | null = null;

  void providerPromise.then((provider) => {
    resolved = provider;
    if (destroyed) {
      provider.destroy();
      return;
    }
    provider.setListings(listings);
    provider.setCampuses(campuses);
    provider.setSelection(selectedId);
    provider.setRoute(routeValue);
    provider.setPlaces(placesValue);
  }).catch(() => {
    if (!destroyed) element.dataset.tileStatus = config.enabled ? "error" : "disabled";
  });

  return {
    setListings(value) {
      listings = value;
      resolved?.setListings(value);
    },
    setCampuses(value) {
      campuses = value;
      resolved?.setCampuses(value);
    },
    setSelection(value) {
      selectedId = value;
      resolved?.setSelection(value);
    },
    setRoute(value) {
      routeValue = value;
      resolved?.setRoute(value);
    },
    setPlaces(value) {
      placesValue = value;
      resolved?.setPlaces(value);
    },
    getListingLayerSnapshot() {
      return resolved?.getListingLayerSnapshot() ?? UNAVAILABLE_LISTING_SNAPSHOT;
    },
    destroy() {
      if (destroyed) return;
      destroyed = true;
      resolved?.destroy();
      resolved = null;
    },
  };
}
