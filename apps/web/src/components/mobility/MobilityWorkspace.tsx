"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import dynamic from "next/dynamic";
import type {
  Campus,
  CampusId,
  CatalogListing,
  NearbyRequest,
  NearbyResult,
  PlaceCategory,
  RouteRequest,
  RouteResult,
  TravelMode,
} from "@/lib/mobility-contracts";
import {
  getMobilityCampuses,
  getMobilityCatalog,
  MobilityApiError,
  postMobilityNearby,
  postMobilityRoute,
} from "./client-api";
import MobilityDetails from "./MobilityDetails";
import type { MobilityMapConfig } from "@/lib/config";
import {
  normalizeMapSearch,
  scrollMapSelection,
  sortMapListingsByPrice,
  type PriceOrder,
} from "@/lib/map-ui";
import {
  formatDistance,
  formatDuration,
  localDateTimeInput,
  localDateTimeWithOffset,
  nearbyStatusLabel,
  PLACE_CATEGORIES,
  routeStatusLabel,
  TRAVEL_MODES,
} from "./mobility-format";

const MobilityMap = dynamic(() => import("./MobilityMap"), {
  ssr: false,
  loading: () => (
    <section
      data-testid="mobility-map-loading"
      aria-label="Đang tải bản đồ"
      className="grid h-[360px] place-items-center rounded-xl border border-slate-200 bg-slate-100 text-sm text-slate-600"
    >
      Đang tải bản đồ di chuyển…
    </section>
  ),
});

type RouteView =
  | { kind: "pending" }
  | { kind: "result"; value: RouteResult }
  | { kind: "error"; message: string };

type NearbyView =
  | { kind: "pending" }
  | { kind: "result"; value: NearbyResult }
  | { kind: "error"; message: string };

function currentRouteIdentity(request: RouteRequest): string {
  return JSON.stringify([
    request.listing_id,
    request.campus_id,
    request.requested_mode,
    request.departure_time ?? null,
  ]);
}

function currentNearbyIdentity(request: NearbyRequest): string {
  return JSON.stringify([
    request.listing_id,
    request.radius_m,
    request.categories,
  ]);
}

function evidenceLabel(kind: RouteResult["evidence_kind"] | NearbyResult["evidence_kind"]): string {
  if (kind === "SYNTHETIC_FIXTURE") return "Dữ liệu tổng hợp dùng cho thử nghiệm";
  if (kind === "LIVE") return "Dữ liệu trực tiếp từ provider";
  return "Chưa có dữ liệu quan sát";
}

function errorMessage(error: unknown): string {
  return error instanceof MobilityApiError
    ? error.message
    : "Dịch vụ di chuyển hiện chưa thể trả lời.";
}

function RouteResultCard({
  campus,
  state,
}: {
  campus: Campus;
  state: RouteView;
}) {
  const status = state.kind === "result"
    ? state.value.status
    : state.kind === "pending"
      ? "PENDING"
      : "REQUEST_ERROR";

  return (
    <article
      data-testid={`route-result-${campus.id}`}
      data-status={status}
      className="rounded-lg border border-slate-200 bg-white p-3"
      aria-live="polite"
    >
      <h4 className="font-medium text-slate-900">{campus.name}</h4>
      {state.kind === "pending" ? (
        <p className="mt-1 text-sm text-slate-600">Đang tính tuyến tới khuôn viên này…</p>
      ) : state.kind === "error" ? (
        <p className="mt-1 text-sm text-rose-800">{state.message}</p>
      ) : (
        <>
          <p className="mt-1 text-sm text-slate-700">{routeStatusLabel(state.value.status)}</p>
          {state.value.status === "OK" && (
            <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-sm text-slate-700">
              <span>
                Thời gian: {state.value.duration_seconds == null
                  ? "chưa có số đo"
                  : formatDuration(state.value.duration_seconds)}
              </span>
              <span>
                Quãng đường: {state.value.distance_meters == null
                  ? "chưa có số đo"
                  : formatDistance(state.value.distance_meters)}
              </span>
            </div>
          )}
          <p
            data-evidence-kind={state.value.evidence_kind}
            className="mt-2 text-xs text-slate-600"
          >
            {evidenceLabel(state.value.evidence_kind)}
          </p>
          {state.value.warnings.map((warning, index) => (
            <p
              key={`${warning.code}-${index}`}
              className="mt-2 rounded-md bg-amber-50 px-2.5 py-2 text-xs text-amber-950"
            >
              {warning.message}
            </p>
          ))}
        </>
      )}
    </article>
  );
}

export default function MobilityWorkspace({ mapConfig }: { mapConfig: MobilityMapConfig }) {
  const [campuses, setCampuses] = useState<Campus[]>([]);
  const [listings, setListings] = useState<CatalogListing[]>([]);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [selectedListingId, setSelectedListingId] = useState<number | null>(null);
  const [selectedCampusId, setSelectedCampusId] = useState<CampusId | "">("");
  const [searchQuery, setSearchQuery] = useState("");
  const [priceOrder, setPriceOrder] = useState<PriceOrder>("original");
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const listingScrollContainerRef = useRef<HTMLDivElement>(null);
  const [mode, setMode] = useState<TravelMode>("MOTORBIKE");
  const [departureLocal, setDepartureLocal] = useState(() =>
    localDateTimeInput(new Date(Date.now() + 60 * 60 * 1000)),
  );
  const [radius, setRadius] = useState<NearbyRequest["radius_m"]>(1000);
  const [categories, setCategories] = useState<PlaceCategory[]>(
    PLACE_CATEGORIES.map((category) => category.value),
  );
  const [routeViews, setRouteViews] = useState<Partial<Record<CampusId, RouteView>>>({});
  const [nearbyView, setNearbyView] = useState<NearbyView | null>(null);
  const routeGeneration = useRef(0);
  const nearbyGeneration = useRef(0);
  const routeIdentities = useRef(new Map<CampusId, string>());
  const nearbyIdentity = useRef<string | null>(null);
  const routeControllers = useRef(new Set<AbortController>());
  const nearbyController = useRef<AbortController | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    let current = true;
    setLoading(true);
    Promise.all([
      getMobilityCampuses(controller.signal),
      getMobilityCatalog(controller.signal),
    ])
      .then(([campusRows, listingRows]) => {
        if (!current) return;
        setCampuses(campusRows);
        setListings(listingRows);
        setSelectedCampusId(campusRows[0]?.id ?? "");
        setLoadError(null);
      })
      .catch((error: unknown) => {
        if (!current || controller.signal.aborted) return;
        setLoadError(errorMessage(error));
      })
      .finally(() => {
        if (current) setLoading(false);
      });
    return () => {
      current = false;
      controller.abort();
    };
  }, []);

  useEffect(() => () => {
    routeGeneration.current += 1;
    nearbyGeneration.current += 1;
    for (const controller of routeControllers.current) controller.abort();
    routeControllers.current.clear();
    nearbyController.current?.abort();
    nearbyController.current = null;
    routeIdentities.current.clear();
    nearbyIdentity.current = null;
  }, []);

  const selectedListing = useMemo(
    () => listings.find((listing) => listing.id === selectedListingId) ?? null,
    [listings, selectedListingId],
  );
  const selectedCampus = campuses.find((campus) => campus.id === selectedCampusId) ?? null;
  const filteredListings = useMemo(() => {
    const normalizedQuery = normalizeMapSearch(searchQuery.trim());
    if (normalizedQuery.length === 0) return listings;

    return listings.filter((listing) =>
      normalizeMapSearch(listing.title).includes(normalizedQuery) ||
      normalizeMapSearch(listing.address).includes(normalizedQuery),
    );
  }, [listings, searchQuery]);
  const visibleListings = useMemo(
    () => sortMapListingsByPrice(filteredListings, priceOrder),
    [filteredListings, priceOrder],
  );

  function cancelRoutes() {
    routeGeneration.current += 1;
    for (const controller of routeControllers.current) controller.abort();
    routeControllers.current.clear();
    routeIdentities.current.clear();
    setRouteViews({});
  }

  function cancelNearby() {
    nearbyGeneration.current += 1;
    nearbyController.current?.abort();
    nearbyController.current = null;
    nearbyIdentity.current = null;
    setNearbyView(null);
  }

  function selectListing(id: number) {
    cancelRoutes();
    cancelNearby();
    setSelectedListingId(id);
    scrollMapSelection(listingScrollContainerRef.current, id);
  }

  function changeSearch(value: string) {
    const normalizedQuery = normalizeMapSearch(value.trim());
    const nextFilteredListings = normalizedQuery.length === 0
      ? listings
      : listings.filter((listing) =>
          normalizeMapSearch(listing.title).includes(normalizedQuery) ||
          normalizeMapSearch(listing.address).includes(normalizedQuery),
        );

    if (
      selectedListingId !== null &&
      !nextFilteredListings.some((listing) => listing.id === selectedListingId)
    ) {
      cancelRoutes();
      cancelNearby();
      setSelectedListingId(null);
    }
    setSearchQuery(value);
  }

  function routeIsCurrent(campusId: CampusId, identity: string, generation: number) {
    return (
      routeGeneration.current === generation &&
      routeIdentities.current.get(campusId) === identity
    );
  }

  function startRoutes(targets: Campus[]) {
    if (!selectedListing || selectedListing.position == null || targets.length === 0) return;
    routeGeneration.current += 1;
    const generation = routeGeneration.current;
    for (const controller of routeControllers.current) controller.abort();
    routeControllers.current.clear();
    routeIdentities.current.clear();

    const departureTime = mode === "BUS"
      ? localDateTimeWithOffset(departureLocal)
      : null;
    if (mode === "BUS" && !departureTime) {
      setRouteViews({
        [targets[0].id]: {
          kind: "error",
          message: "Hãy chọn giờ xe buýt hợp lệ theo giờ địa phương.",
        },
      });
      return;
    }

    const requests = targets.map((campus) => {
      const body: RouteRequest = {
        listing_id: selectedListing.id,
        campus_id: campus.id,
        requested_mode: mode,
        ...(departureTime ? { departure_time: departureTime } : {}),
        direction: "LISTING_TO_CAMPUS",
      };
      const identity = currentRouteIdentity(body);
      routeIdentities.current.set(campus.id, identity);
      return { campus, body, identity };
    });
    setRouteViews(Object.fromEntries(requests.map(({ campus }) => [campus.id, { kind: "pending" }])));

    for (const { campus, body, identity } of requests) {
      const controller = new AbortController();
      routeControllers.current.add(controller);
      void postMobilityRoute(body, controller.signal)
        .then((result) => {
          if (
            !routeIsCurrent(campus.id, identity, generation) ||
            result.listing_id !== body.listing_id ||
            result.campus_id !== body.campus_id ||
            result.requested_mode !== body.requested_mode
          ) {
            return;
          }
          setRouteViews((previous) =>
            routeIsCurrent(campus.id, identity, generation)
              ? { ...previous, [campus.id]: { kind: "result", value: result } }
              : previous,
          );
        })
        .catch((error: unknown) => {
          if (!routeIsCurrent(campus.id, identity, generation)) return;
          setRouteViews((previous) =>
            routeIsCurrent(campus.id, identity, generation)
              ? { ...previous, [campus.id]: { kind: "error", message: errorMessage(error) } }
              : previous,
          );
        })
        .finally(() => routeControllers.current.delete(controller));
    }
  }

  function nearbyIsCurrent(identity: string, generation: number) {
    return nearbyGeneration.current === generation && nearbyIdentity.current === identity;
  }

  function startNearby() {
    if (!selectedListing || selectedListing.position == null || categories.length === 0) return;
    nearbyGeneration.current += 1;
    const generation = nearbyGeneration.current;
    nearbyController.current?.abort();
    const controller = new AbortController();
    nearbyController.current = controller;
    const requestedCategories = [...categories];
    const body: NearbyRequest = {
      listing_id: selectedListing.id,
      radius_m: radius,
      categories: requestedCategories,
    };
    const identity = currentNearbyIdentity(body);
    nearbyIdentity.current = identity;
    setNearbyView({ kind: "pending" });

    void postMobilityNearby(body, controller.signal)
      .then((result) => {
        if (
          !nearbyIsCurrent(identity, generation) ||
          result.listing_id !== body.listing_id ||
          result.radius_m !== body.radius_m ||
          result.categories.length !== requestedCategories.length ||
          requestedCategories.some((category, index) => result.categories[index] !== category)
        ) {
          return;
        }
        setNearbyView((previous) =>
          nearbyIsCurrent(identity, generation)
            ? { kind: "result", value: result }
            : previous,
        );
      })
      .catch((error: unknown) => {
        if (!nearbyIsCurrent(identity, generation)) return;
        setNearbyView((previous) =>
          nearbyIsCurrent(identity, generation)
            ? { kind: "error", message: errorMessage(error) }
            : previous,
        );
      })
      .finally(() => {
        if (nearbyController.current === controller) nearbyController.current = null;
      });
  }

  function changeCampus(value: CampusId | "") {
    cancelRoutes();
    setSelectedCampusId(value);
  }

  function changeMode(value: TravelMode) {
    cancelRoutes();
    setMode(value);
  }

  function changeDeparture(value: string) {
    cancelRoutes();
    setDepartureLocal(value);
  }

  function changeRadius(value: NearbyRequest["radius_m"]) {
    cancelNearby();
    setRadius(value);
  }

  function changeCategories(value: PlaceCategory[]) {
    cancelNearby();
    setCategories(value);
  }

  const canRequest = Boolean(selectedListing?.position);
  const nearbyResult = nearbyView?.kind === "result" ? nearbyView.value : null;
  const routeResults = useMemo(() => Object.fromEntries(
    Object.entries(routeViews).flatMap(([campusId, state]) =>
      state?.kind === "result" ? [[campusId, state.value]] : [],
    ),
  ) as Partial<Record<CampusId, RouteResult>>, [routeViews]);
  const visibleRoute = selectedCampusId ? routeResults[selectedCampusId] ?? null : null;

  return (
    <main className="min-h-screen bg-slate-50 text-slate-800">
      <header className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-200 bg-white px-4 py-3 shadow-sm">
        <a href="/" className="flex items-center gap-3" aria-label="Trọ CTU, trang chủ">
          <span className="grid h-9 w-9 place-items-center rounded-full bg-emerald-700 font-bold text-white">T</span>
          <span className="font-semibold text-slate-900">Trọ CTU</span>
        </a>
      </header>

      <div className="mx-auto max-w-[1600px] px-3 py-4 sm:px-5">
        <h1 className="mb-4 text-2xl font-semibold text-slate-900">Bản đồ di chuyển</h1>
        {loadError && (
          <p role="alert" className="mb-4 rounded-lg bg-rose-50 px-4 py-3 text-sm text-rose-900">
            {loadError}
          </p>
        )}
        <div className="mb-2 flex justify-end">
          <button
            type="button"
            aria-controls="mobility-listing-sidebar"
            aria-expanded={!sidebarCollapsed}
            onClick={() => setSidebarCollapsed((collapsed) => !collapsed)}
            className="rounded-md border border-slate-300 bg-white px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-emerald-700"
          >
            {sidebarCollapsed ? "Mở danh sách tin" : "Thu gọn danh sách tin"}
          </button>
        </div>
        <div className={`grid gap-4 ${sidebarCollapsed ? "grid-cols-1" : "xl:grid-cols-[350px_minmax(0,1fr)]"}`}>
          <aside
            id="mobility-listing-sidebar"
            aria-label="Danh sách tin"
            hidden={sidebarCollapsed}
            className={`${sidebarCollapsed ? "hidden" : "flex"} max-h-[82vh] min-h-[440px] flex-col overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm`}
          >
            <div className="border-b border-slate-100 px-4 py-3">
              <div className="flex items-center justify-between gap-2">
              <div>
                <h2 className="font-semibold text-slate-900">Danh mục chỗ ở</h2>
                <p data-testid="catalog-count" className="mt-1 text-xs text-slate-600">
                  {loading ? "Đang tải danh mục…" : `${listings.length} tin`}
                </p>
              </div>
              <span className="text-xs text-slate-500">Tin chưa có tọa độ vẫn được giữ</span>
              </div>
              <div className="mt-3 grid gap-2 sm:grid-cols-2">
                <label className="block text-xs font-medium text-slate-700 sm:col-span-2">
                  Tìm tin theo tên hoặc địa chỉ
                  <input
                    type="search"
                    aria-label="Tìm tin theo tên hoặc địa chỉ"
                    value={searchQuery}
                    onChange={(event) => changeSearch(event.target.value)}
                    disabled={loading || Boolean(loadError)}
                    className="mt-1 block w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm font-normal"
                  />
                </label>
                <label className="block text-xs font-medium text-slate-700">
                  Sắp xếp giá
                  <select
                    aria-label="Sắp xếp giá"
                    value={priceOrder}
                    onChange={(event) => setPriceOrder(event.target.value as PriceOrder)}
                    disabled={loading || Boolean(loadError)}
                    className="mt-1 block w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm font-normal"
                  >
                    <option value="original">Thứ tự ban đầu</option>
                    <option value="price_asc">Giá tăng dần</option>
                    <option value="price_desc">Giá giảm dần</option>
                  </select>
                </label>
                <p data-testid="filtered-count" className="self-end pb-2 text-xs text-slate-600">
                  {loading ? "Đang lọc…" : `${visibleListings.length} tin hiển thị`}
                </p>
              </div>
            </div>
            <div ref={listingScrollContainerRef} className="min-h-0 flex-1 overflow-y-auto">
              {loading && (
                <p className="px-4 py-8 text-sm text-slate-600">Đang tải các trang tin…</p>
              )}
              {!loading && !loadError && visibleListings.length === 0 && (
                <p className="px-4 py-8 text-sm text-slate-600">
                  {listings.length === 0 ? "Danh mục hiện chưa có tin." : "Không có tin phù hợp."}
                </p>
              )}
              <ul>
                {visibleListings.map((listing) => {
                  const selected = listing.id === selectedListingId;
                  return (
                    <li key={listing.id} className="border-b border-slate-100 last:border-0">
                      <button
                        type="button"
                        data-listing-id={listing.id}
                        aria-pressed={selected}
                        onClick={() => selectListing(listing.id)}
                        className={`w-full px-4 py-3 text-left transition hover:bg-slate-50 ${selected ? "bg-emerald-50" : "bg-white"}`}
                      >
                        <span className="block line-clamp-2 text-sm font-medium text-slate-900">
                          {listing.title}
                        </span>
                        <span className="mt-1 block text-sm font-semibold text-emerald-800">
                          {listing.price == null ? "Giá chưa rõ" : `${new Intl.NumberFormat("vi-VN").format(listing.price)} đ/tháng`}
                        </span>
                        <span className="mt-1 block text-xs text-slate-600">
                          {listing.area == null ? "Diện tích chưa rõ" : `${listing.area} m²`}
                          {listing.district ? ` · ${listing.district}` : ""}
                        </span>
                        {listing.position == null && (
                          <span className="mt-1 block text-xs text-amber-900">Chưa có tọa độ · vẫn có trong danh sách</span>
                        )}
                      </button>
                    </li>
                  );
                })}
              </ul>
            </div>
          </aside>

          <section className="min-w-0 space-y-4">
            <MobilityMap
              config={mapConfig}
              listings={filteredListings}
              campuses={campuses}
              selectedListingId={selectedListingId}
              route={visibleRoute}
              nearby={nearbyResult}
              onSelect={selectListing}
            />

            <div className="grid gap-4 2xl:grid-cols-[minmax(280px,0.8fr)_minmax(360px,1.2fr)]">
              <section aria-label="Công cụ tuyến và tiện ích" className="space-y-4 rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
                <div>
                  <h2 className="font-semibold text-slate-900">Tuyến đến khuôn viên</h2>
                  <p className="mt-1 text-xs text-slate-600">
                    Tuyến đi từ chỗ ở đến khuôn viên được chọn.
                  </p>
                  <p className="mt-1 text-xs text-amber-900">
                    Tọa độ khuôn viên và lối vào chưa được xác minh.
                  </p>
                </div>
                <div className="grid gap-3 sm:grid-cols-2 2xl:grid-cols-1">
                  <label className="block text-sm font-medium text-slate-700">
                    Khuôn viên
                    <select
                      aria-label="Khuôn viên"
                      value={selectedCampusId}
                      onChange={(event) => changeCampus(event.target.value as CampusId | "")}
                      disabled={loading || campuses.length === 0}
                      className="mt-1 block w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm"
                    >
                      {campuses.map((campus) => (
                        <option key={campus.id} value={campus.id}>{campus.name}</option>
                      ))}
                    </select>
                  </label>
                  <label className="block text-sm font-medium text-slate-700">
                    Phương tiện
                    <select
                      aria-label="Phương tiện"
                      value={mode}
                      onChange={(event) => changeMode(event.target.value as TravelMode)}
                      className="mt-1 block w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm"
                    >
                      {TRAVEL_MODES.map((option) => (
                        <option key={option.value} value={option.value}>
                          {option.value === "MOTORBIKE" || option.value === "BUS"
                            ? `${option.label} · chưa được hỗ trợ`
                            : option.label}
                        </option>
                      ))}
                    </select>
                  </label>
                </div>
                {mode === "BUS" && (
                  <label className="block text-sm font-medium text-slate-700">
                    Giờ khởi hành xe buýt
                    <input
                      type="datetime-local"
                      aria-label="Giờ khởi hành xe buýt"
                      value={departureLocal}
                      onChange={(event) => changeDeparture(event.target.value)}
                      className="mt-1 block w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm"
                    />
                    <span className="mt-1 block text-xs font-normal text-slate-500">
                      Giờ địa phương; yêu cầu gửi kèm độ lệch múi giờ của thiết bị.
                    </span>
                  </label>
                )}
                {!canRequest && selectedListing && (
                  <p className="rounded-md bg-amber-50 px-3 py-2 text-sm text-amber-950">
                    Tin này chưa có tọa độ nên chưa thể tính tuyến hoặc tìm tiện ích.
                  </p>
                )}
                <div className="flex flex-wrap gap-2">
                  <button
                    type="button"
                    disabled={!canRequest || !selectedCampus}
                    onClick={() => selectedCampus && startRoutes([selectedCampus])}
                    className="rounded-md bg-emerald-700 px-3 py-2 text-sm font-medium text-white hover:bg-emerald-800 disabled:cursor-not-allowed disabled:bg-slate-300"
                  >
                    Tính tuyến tới khu đã chọn
                  </button>
                  <button
                    type="button"
                    disabled={!canRequest || campuses.length !== 3}
                    onClick={() => startRoutes(campuses)}
                    className="rounded-md border border-slate-300 px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:cursor-not-allowed disabled:text-slate-400"
                  >
                    Tính tới cả 3 khu
                  </button>
                </div>
                <div className="space-y-2">
                  {campuses.flatMap((campus) => {
                    const state = routeViews[campus.id];
                    return state ? [<RouteResultCard key={campus.id} campus={campus} state={state} />] : [];
                  })}
                </div>

                <div className="border-t border-slate-200 pt-4">
                  <h3 className="font-semibold text-slate-900">Tiện ích quanh tin</h3>
                  <p className="mt-1 text-xs text-slate-600">
                    Bán kính địa lý; khoảng cách tới từng điểm là đường thẳng. Kết quả không cam kết bao phủ mọi tiện ích.
                  </p>
                  <div className="mt-3 grid gap-3 sm:grid-cols-2 2xl:grid-cols-1">
                    <label className="block text-sm font-medium text-slate-700">
                      Bán kính tiện ích
                      <select
                        aria-label="Bán kính tiện ích"
                        value={radius}
                        onChange={(event) => changeRadius(Number(event.target.value) as NearbyRequest["radius_m"])}
                        className="mt-1 block w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm"
                      >
                        <option value={500}>500 m</option>
                        <option value={1000}>1.000 m</option>
                        <option value={2000}>2.000 m</option>
                      </select>
                    </label>
                    <label className="block text-sm font-medium text-slate-700">
                      Danh mục tiện ích
                      <select
                        aria-label="Danh mục tiện ích"
                        multiple
                        value={categories}
                        onChange={(event) =>
                          changeCategories(
                            Array.from(event.target.selectedOptions, (option) => option.value as PlaceCategory),
                          )
                        }
                        className="mt-1 block min-h-28 w-full rounded-md border border-slate-300 bg-white px-2 py-1 text-sm"
                      >
                        {PLACE_CATEGORIES.map((option) => (
                          <option key={option.value} value={option.value}>{option.label}</option>
                        ))}
                      </select>
                      <span className="mt-1 block text-xs font-normal text-slate-500">
                        Giữ Ctrl hoặc Command để chọn nhiều nhóm.
                      </span>
                    </label>
                  </div>
                  <button
                    type="button"
                    disabled={!canRequest || categories.length === 0}
                    onClick={startNearby}
                    className="mt-3 rounded-md bg-slate-800 px-3 py-2 text-sm font-medium text-white hover:bg-slate-900 disabled:cursor-not-allowed disabled:bg-slate-300"
                  >
                    Tìm tiện ích quanh tin
                  </button>
                  {nearbyView && (
                    <NearbyResultPanel state={nearbyView} />
                  )}
                </div>
              </section>

              <section aria-label="Chi tiết tin được chọn" className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
                {selectedListing ? (
                  <MobilityDetails listing={selectedListing} />
                ) : (
                  <div className="py-8 text-center text-sm text-slate-600">
                    {loading ? "Đang tải danh mục…" : "Chọn một tin để xem chi tiết và công cụ di chuyển."}
                  </div>
                )}
              </section>
            </div>
          </section>
        </div>
      </div>
    </main>
  );
}

function NearbyResultPanel({ state }: { state: NearbyView }) {
  const status = state.kind === "result"
    ? state.value.status
    : state.kind === "pending"
      ? "PENDING"
      : "REQUEST_ERROR";
  return (
    <section
      data-testid="nearby-result"
      data-status={status}
      className="mt-3 rounded-lg border border-slate-200 p-3"
      aria-live="polite"
    >
      {state.kind === "pending" ? (
        <p className="text-sm text-slate-600">Đang tìm trong bán kính đã chọn…</p>
      ) : state.kind === "error" ? (
        <p className="text-sm text-rose-800">{state.message}</p>
      ) : (
        <>
          <p className="text-sm font-medium text-slate-900">{nearbyStatusLabel(state.value.status)}</p>
          <p className="mt-1 text-xs text-slate-600">Bán kính {new Intl.NumberFormat("vi-VN").format(state.value.radius_m)} m</p>
          <p
            data-evidence-kind={state.value.evidence_kind}
            className="mt-1 text-xs text-slate-600"
          >
            {evidenceLabel(state.value.evidence_kind)}
          </p>
          <p className="mt-1 text-xs text-slate-600">
            {state.value.coverage === "PARTIAL"
              ? "Độ phủ một phần; phản hồi không đại diện cho mọi tiện ích."
              : "Chưa xác định được độ phủ."}
          </p>
          {state.value.items.length > 0 && (
            <ul className="mt-2 space-y-2">
              {state.value.items.map((place) => (
                <li key={place.provider_place_id} className="rounded-md bg-slate-50 px-3 py-2">
                  <p className="text-sm font-medium text-slate-800">{place.name}</p>
                  <p className="text-xs text-slate-600">
                    {place.straight_line_distance_m == null
                      ? "Khoảng cách đường thẳng chưa rõ"
                      : `${formatDistance(place.straight_line_distance_m)} · khoảng cách đường thẳng`}
                  </p>
                </li>
              ))}
            </ul>
          )}
        </>
      )}
    </section>
  );
}
