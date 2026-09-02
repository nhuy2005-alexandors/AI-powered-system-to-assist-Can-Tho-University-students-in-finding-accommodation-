"use client";

import Link from "next/link";
import dynamic from "next/dynamic";
import { useMemo, useState, useTransition } from "react";
import { useRouter } from "next/navigation";
import { getListingRoute, type ListingOut } from "@/lib/api";
import { formatPrice } from "@/lib/format";

// react-leaflet đụng window ngay khi import → phải tắt SSR, nếu không build
// Next lỗi "window is not defined" lúc render phía server.
const MapCanvas = dynamic(() => import("./MapCanvas"), {
  ssr: false,
  loading: () => (
    <div className="flex h-full w-full items-center justify-center bg-tint text-sm text-ink-faint">
      Đang tải bản đồ...
    </div>
  ),
});

// Index khớp CAMPUSES trong apps/api/app/listings/routing.py (0=khu I,1=khu II,2=khu III).
const CAMPUS_LABELS = ["Khu I", "Khu II", "Khu III"];

export type ListingWithCoords = ListingOut & { lat: number; lng: number };

export default function MapScreen({
  items,
  radius,
  error,
}: {
  items: ListingOut[];
  radius: number;
  error: string | null;
}) {
  const router = useRouter();
  const [isPending, startTransition] = useTransition();
  const [campus, setCampus] = useState(1); // mặc định khu II (FR-M.3)
  const [radiusDraft, setRadiusDraft] = useState(radius);
  const [selected, setSelected] = useState<ListingWithCoords | null>(null);
  const [route, setRoute] = useState<[number, number][] | null>(null);

  const withCoords = useMemo(
    () => items.filter((l): l is ListingWithCoords => l.lat != null && l.lng != null),
    [items],
  );

  async function drawRoute(listing: ListingWithCoords, campusIdx: number) {
    try {
      const path = await getListingRoute(listing.id, campusIdx);
      setRoute(path as [number, number][]);
    } catch {
      // ORS chưa cấu hình / lỗi mạng — không vẽ đường, không chặn UI (FR-M.8)
      setRoute(null);
    }
  }

  function selectListing(listing: ListingWithCoords) {
    setSelected(listing);
    setRoute(null);
    void drawRoute(listing, campus);
  }

  function changeCampus(idx: number) {
    setCampus(idx);
    setRoute(null);
    if (selected) void drawRoute(selected, idx);
  }

  function commitRadius() {
    if (radiusDraft !== radius) {
      startTransition(() => router.replace(`/map?radius=${radiusDraft}`, { scroll: false }));
    }
  }

  function minutesLabel(listing: ListingOut): string | null {
    const minutes = listing.route_time_campus?.[campus];
    if (minutes == null) return null;
    return `${Math.round(minutes)} phút tới ${CAMPUS_LABELS[campus].toLowerCase()}`;
  }

  return (
    <div className="flex min-h-0 flex-1 flex-col-reverse lg:grid lg:grid-cols-[400px_minmax(0,1fr)]">
      {/* Sidebar danh sách tin (mockup 03) */}
      <aside className="flex min-h-0 flex-1 flex-col border-t border-line bg-white lg:border-r lg:border-t-0">
        <div className="border-b border-line-soft px-5 py-4">
          <h1 className="text-[17px] font-bold text-ink">
            {withCoords.length} tin trong bán kính {(radius / 1000).toFixed(1)} km
          </h1>
          <div className="mt-3 flex gap-1.5 rounded-[11px] bg-tint p-1">
            {CAMPUS_LABELS.map((label, i) => (
              <button
                key={label}
                type="button"
                onClick={() => changeCampus(i)}
                className={`flex-1 rounded-lg py-2 text-sm transition ${
                  campus === i
                    ? "bg-primary font-semibold text-white"
                    : "text-ink-soft hover:bg-white/70"
                }`}
              >
                {label}
              </button>
            ))}
          </div>
          <p className="mt-2.5 text-[13px] text-ink-muted">
            Bấm một tin để vẽ đường đi từ {CAMPUS_LABELS[campus].toLowerCase()} tới phòng.
          </p>
        </div>

        {error && (
          <p className="mx-3 mt-3 rounded-md bg-rose-50 px-3 py-2 text-sm text-rose-600">{error}</p>
        )}
        {!error && withCoords.length === 0 && (
          <p className="mt-10 px-4 text-center text-ink-muted">
            Không tìm thấy tin nào trong bán kính này
          </p>
        )}

        <div
          className={`flex min-h-0 flex-1 flex-col gap-2.5 overflow-y-auto p-3 ${
            isPending ? "opacity-50" : ""
          }`}
        >
          {withCoords.map((listing) => {
            const isSelected = selected?.id === listing.id;
            const meta = [
              listing.area != null ? `${listing.area} m²` : null,
              listing.district,
              minutesLabel(listing),
            ]
              .filter(Boolean)
              .join(" · ");

            return (
              <button
                key={listing.id}
                type="button"
                onClick={() => selectListing(listing)}
                className={`flex gap-3 rounded-[13px] border p-3 text-left transition ${
                  isSelected
                    ? "border-primary-ring bg-primary-soft"
                    : "border-line-soft hover:border-primary-ring hover:bg-paper"
                }`}
              >
                {listing.images[0] ? (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img
                    src={listing.images[0]}
                    alt=""
                    className="h-[74px] w-[84px] shrink-0 rounded-[10px] object-cover"
                  />
                ) : (
                  <span className="photo-placeholder h-[74px] w-[84px] shrink-0 rounded-[10px]" />
                )}
                <span className="flex min-w-0 flex-col gap-1">
                  <span className="line-clamp-2 text-[14.5px] font-semibold leading-tight text-ink">
                    {listing.title}
                  </span>
                  <span className="text-base font-bold text-primary">
                    {formatPrice(listing.price)}
                  </span>
                  {meta && <span className="truncate text-[13px] text-ink-muted">{meta}</span>}
                </span>
              </button>
            );
          })}
        </div>
      </aside>

      {/* Bản đồ + các control nổi */}
      <div className="relative h-[52vh] min-h-0 lg:h-auto">
        <MapCanvas
          items={withCoords}
          campus={campus}
          radius={radius}
          selectedId={selected?.id ?? null}
          route={route}
          onSelect={selectListing}
        />

        {/* Điều khiển bán kính — góc phải trên theo mockup */}
        <div className="absolute right-4 top-4 z-[1000] flex w-[180px] flex-col gap-2 rounded-xl border border-line bg-white px-3.5 py-3 shadow-md">
          <span className="text-[13.5px] font-bold text-ink">
            Bán kính {(radiusDraft / 1000).toFixed(1)} km
          </span>
          <input
            type="range"
            min={500}
            max={5000}
            step={250}
            value={radiusDraft}
            onChange={(e) => setRadiusDraft(Number(e.target.value))}
            onPointerUp={commitRadius}
            onKeyUp={commitRadius}
            className="accent-[#0b4d8f]"
            aria-label="Bán kính tìm kiếm"
          />
        </div>

        {/* Card tin đang chọn — thay Popup Leaflet vì nhiều tin trùng toạ độ
            nằm trong cluster, popup không mở được từ danh sách bên trái. */}
        {selected && (
          <div className="absolute bottom-5 left-4 z-[1000] w-[270px] rounded-[14px] border border-line bg-white p-3.5 shadow-xl">
            <button
              type="button"
              onClick={() => {
                setSelected(null);
                setRoute(null);
              }}
              className="absolute right-2.5 top-2.5 z-10 flex h-7 w-7 items-center justify-center rounded-full bg-white/90 text-lg text-ink-muted shadow-sm hover:text-ink"
              aria-label="Đóng"
            >
              ×
            </button>
            {selected.images[0] ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img
                src={selected.images[0]}
                alt=""
                className="h-[110px] w-full rounded-[9px] object-cover"
              />
            ) : (
              <div className="photo-placeholder h-[84px] w-full rounded-[9px]" />
            )}
            <p className="mt-2.5 line-clamp-2 text-[14.5px] font-semibold leading-tight text-ink">
              {selected.title}
            </p>
            <p className="mt-1 text-[17px] font-bold text-primary">{formatPrice(selected.price)}</p>
            {selected.address && (
              <p className="mt-1 line-clamp-2 text-[13px] text-ink-muted">{selected.address}</p>
            )}
            <p className="mt-1 text-[13px] text-ink-muted">
              {minutesLabel(selected) ?? "Chưa có thời gian di chuyển"}
            </p>
            {selected.geocode_confidence && selected.geocode_confidence !== "high" && (
              <p className="mt-1 text-xs text-ink-faint">Vị trí tương đối (chính xác tới cấp đường)</p>
            )}
            <Link
              href={`/listings/${selected.id}`}
              className="mt-2.5 block rounded-[9px] bg-primary py-2.5 text-center text-sm font-semibold text-white transition hover:bg-navy"
            >
              Xem chi tiết
            </Link>
          </div>
        )}
      </div>
    </div>
  );
}
