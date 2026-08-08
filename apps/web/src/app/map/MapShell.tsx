"use client";

import Link from "next/link";
import { useCallback, useMemo, useState } from "react";
import { type ListingOut } from "@/lib/api";
import { CAMPUS_LABELS } from "./campuses";
import MapView from "./MapView";
import ResultList from "./ResultList";

const SORT_OPTIONS = [
  { value: "nearest", label: "Gần trường nhất" },
  { value: "price_asc", label: "Giá thấp → cao" },
  { value: "price_desc", label: "Giá cao → thấp" },
  { value: "quality", label: "Chất lượng" },
] as const;

type SortValue = (typeof SORT_OPTIONS)[number]["value"];

const RADIUS_CHIPS = [1000, 3000, 5000, 10000];

function norm(s: string): string {
  // Bỏ dấu để "duong 3/2" khớp "Đường 3/2" — sidebar filter chạy client-side, không gọi API.
  return s
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "")
    .toLowerCase();
}

export default function MapShell({
  items,
  center,
  radius,
  errorMessage,
}: {
  items: ListingOut[];
  center: [number, number];
  radius: number;
  errorMessage: string | null;
}) {
  const [campus, setCampus] = useState(1); // mặc định khu II (FR-M.3)
  const [query, setQuery] = useState("");
  const [sort, setSort] = useState<SortValue>("nearest");
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [route, setRoute] = useState<[number, number][] | null>(null);
  const [sidebarOpen, setSidebarOpen] = useState(true);

  const visible = useMemo(() => {
    const q = norm(query.trim());
    const filtered = q
      ? items.filter(
          (l) => norm(l.title).includes(q) || norm(l.address ?? "").includes(q),
        )
      : items;

    const big = Number.POSITIVE_INFINITY;
    const copy = [...filtered];
    copy.sort((a, b) => {
      switch (sort) {
        case "price_asc":
          return (a.price ?? big) - (b.price ?? big);
        case "price_desc":
          return (b.price ?? -1) - (a.price ?? -1);
        case "quality":
          return (b.quality_score ?? 0) - (a.quality_score ?? 0);
        default:
          return (
            (a.route_time_campus?.[campus] ?? big) -
            (b.route_time_campus?.[campus] ?? big)
          );
      }
    });
    return copy;
  }, [items, query, sort, campus]);

  const select = useCallback(
    async (id: number) => {
      setSelectedId(id);
      try {
        // Gọi proxy same-origin, KHÔNG gọi thẳng localhost:8000: API chưa bật CORS
        // nên fetch cross-origin bị preflight chặn và đường đi không bao giờ vẽ.
        const res = await fetch(`/api/listings/${id}/route-path?campus=${campus}`);
        if (!res.ok) throw new Error(String(res.status));
        setRoute((await res.json()) as [number, number][]);
      } catch {
        // ORS chưa cấu hình / lỗi mạng — không vẽ đường, không chặn UI (FR-M.8 on-demand)
        setRoute(null);
      }
    },
    [campus],
  );

  return (
    <div className="flex h-screen flex-col bg-white">
      {/* Thanh trên: brand + ô tìm + chip lọc — vai trò như header Google Maps */}
      <header className="z-30 flex shrink-0 flex-wrap items-center gap-3 border-b border-slate-200 px-3 py-2 shadow-sm">
        <Link href="/" className="flex items-center gap-2 pr-1">
          <span className="grid h-8 w-8 place-items-center rounded-full bg-emerald-600 text-sm font-bold text-white">
            T
          </span>
          <span className="hidden text-base font-semibold text-slate-800 sm:inline">
            Trọ CTU
          </span>
        </Link>

        <div className="relative min-w-[220px] flex-1 sm:max-w-md">
          <svg
            aria-hidden="true"
            viewBox="0 0 20 20"
            className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 fill-slate-400"
          >
            <path d="M8 2a6 6 0 104.47 10.03l3.75 3.75 1.41-1.41-3.75-3.75A6 6 0 008 2zm0 2a4 4 0 110 8 4 4 0 010-8z" />
          </svg>
          <input
            type="search"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Tìm theo tên tin hoặc địa chỉ"
            aria-label="Tìm trong kết quả"
            className="w-full rounded-full border border-slate-200 bg-slate-50 py-2 pl-9 pr-9 text-sm text-slate-800 shadow-sm outline-none focus:border-emerald-500 focus:bg-white"
          />
          {query && (
            <button
              type="button"
              onClick={() => setQuery("")}
              aria-label="Xoá từ khoá"
              className="absolute right-2 top-1/2 grid h-6 w-6 -translate-y-1/2 place-items-center rounded-full text-slate-400 hover:bg-slate-200 hover:text-slate-600"
            >
              ✕
            </button>
          )}
        </div>

        <div className="flex flex-wrap items-center gap-2">
          {CAMPUS_LABELS.map((label, i) => (
            <button
              key={label}
              type="button"
              onClick={() => {
                setCampus(i);
                setRoute(null);
              }}
              className={`rounded-full px-3 py-1.5 text-sm font-medium shadow-sm transition ${
                campus === i
                  ? "bg-emerald-600 text-white"
                  : "border border-slate-200 bg-white text-slate-600 hover:bg-slate-100"
              }`}
            >
              {label}
            </button>
          ))}

          <span className="mx-1 hidden h-5 w-px bg-slate-200 sm:block" />

          {RADIUS_CHIPS.map((r) => (
            <Link
              key={r}
              href={`/map?radius=${r}`}
              scroll={false}
              className={`rounded-full px-3 py-1.5 text-sm font-medium shadow-sm transition ${
                radius === r
                  ? "bg-slate-800 text-white"
                  : "border border-slate-200 bg-white text-slate-600 hover:bg-slate-100"
              }`}
            >
              {r / 1000} km
            </Link>
          ))}
        </div>
      </header>

      <div className="relative flex min-h-0 flex-1">
        {/* Panel kết quả bên trái */}
        <aside
          className={`z-20 flex h-full shrink-0 flex-col border-r border-slate-200 bg-white transition-all duration-200 ${
            sidebarOpen ? "w-full sm:w-[380px]" : "w-0 overflow-hidden"
          }`}
        >
          <div className="shrink-0 border-b border-slate-100 px-4 py-3">
            <div className="flex items-baseline justify-between gap-2">
              <h1 className="text-lg font-semibold text-slate-800">Kết quả</h1>
              <label className="flex items-center gap-1 text-xs text-slate-500">
                <span className="hidden sm:inline">Sắp xếp</span>
                <select
                  value={sort}
                  onChange={(e) => setSort(e.target.value as SortValue)}
                  aria-label="Sắp xếp kết quả"
                  className="rounded border border-slate-200 bg-white px-2 py-1 text-xs text-slate-700 outline-none focus:border-emerald-500"
                >
                  {SORT_OPTIONS.map((o) => (
                    <option key={o.value} value={o.value}>
                      {o.label}
                    </option>
                  ))}
                </select>
              </label>
            </div>
            <p className="mt-1 text-xs text-slate-500">
              {visible.length} tin trong {(radius / 1000).toFixed(1)} km quanh ĐH Cần Thơ ·
              thời gian tính tới {CAMPUS_LABELS[campus]}
            </p>
          </div>

          {errorMessage && (
            <p className="m-3 rounded-md bg-rose-50 px-3 py-2 text-sm text-rose-600">
              {errorMessage}
            </p>
          )}

          <ResultList
            items={visible}
            campus={campus}
            selectedId={selectedId}
            onSelect={select}
          />
        </aside>

        {/* Nút thu/mở panel — nằm ở rìa panel như Google Maps */}
        <button
          type="button"
          onClick={() => setSidebarOpen((v) => !v)}
          aria-label={sidebarOpen ? "Thu gọn danh sách" : "Mở danh sách"}
          className="absolute top-1/2 z-30 hidden h-12 w-5 -translate-y-1/2 items-center justify-center rounded-r border border-l-0 border-slate-200 bg-white text-slate-500 shadow-sm hover:bg-slate-50 sm:flex"
          style={{ left: sidebarOpen ? 380 : 0 }}
        >
          {sidebarOpen ? "‹" : "›"}
        </button>

        {/* Map chiếm phần còn lại */}
        <div className="relative min-h-0 flex-1">
          <MapView
            items={visible}
            center={center}
            campus={campus}
            selectedId={selectedId}
            route={route}
            onSelect={select}
          />
        </div>
      </div>
    </div>
  );
}
