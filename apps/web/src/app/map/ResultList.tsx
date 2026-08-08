"use client";

import Link from "next/link";
import { useEffect, useRef } from "react";
import type { ListingOut } from "@/lib/api";
import { formatArea, formatPrice, riskBadge } from "@/lib/format";

// Panel kết quả bên trái (vai trò như cột kết quả của Google Maps): mỗi tin là 1 hàng
// bấm được → chọn tin, map bay tới pin tương ứng + vẽ đường tới campus.
export default function ResultList({
  items,
  campus,
  selectedId,
  onSelect,
}: {
  items: ListingOut[];
  campus: number;
  selectedId: number | null;
  onSelect: (id: number) => void;
}) {
  const listRef = useRef<HTMLUListElement>(null);

  // Chọn tin từ map → cuộn hàng tương ứng vào tầm nhìn (2 chiều map ↔ list).
  useEffect(() => {
    if (selectedId == null || !listRef.current) return;
    const row = listRef.current.querySelector<HTMLElement>(
      `[data-listing-id="${selectedId}"]`,
    );
    row?.scrollIntoView({ block: "nearest", behavior: "smooth" });
  }, [selectedId]);

  if (items.length === 0) {
    return (
      <p className="px-4 py-10 text-center text-sm text-slate-500">
        Không tìm thấy tin nào
      </p>
    );
  }

  return (
    <ul ref={listRef} className="min-h-0 flex-1 divide-y divide-slate-100 overflow-y-auto">
      {items.map((listing) => {
        const minutes = listing.route_time_campus?.[campus] ?? null;
        const badge = riskBadge(listing.risk_level);
        const cover = listing.images[0];
        const selected = listing.id === selectedId;

        return (
          <li key={listing.id} data-listing-id={listing.id}>
            <div
              role="button"
              tabIndex={0}
              onClick={() => onSelect(listing.id)}
              onKeyDown={(e) => {
                if (e.key === "Enter" || e.key === " ") {
                  e.preventDefault();
                  onSelect(listing.id);
                }
              }}
              className={`flex w-full cursor-pointer gap-3 px-4 py-3 text-left transition ${
                selected ? "bg-emerald-50" : "hover:bg-slate-50"
              }`}
            >
              <div className="min-w-0 flex-1">
                <p className="line-clamp-2 text-sm font-medium text-slate-800">
                  {listing.title}
                </p>

                <p className="mt-0.5 text-sm font-semibold text-emerald-700">
                  {formatPrice(listing.price)}
                </p>

                <div className="mt-0.5 flex flex-wrap items-center gap-x-2 text-xs text-slate-500">
                  {listing.area != null && <span>{formatArea(listing.area)}</span>}
                  {listing.district && <span>{listing.district}</span>}
                  <span
                    className={`rounded-full px-1.5 py-0.5 font-medium ${badge.className}`}
                  >
                    {badge.label}
                  </span>
                </div>

                {listing.address && (
                  <p className="mt-0.5 line-clamp-1 text-xs text-slate-500">
                    {listing.address}
                  </p>
                )}

                <p className="mt-0.5 text-xs text-slate-400">
                  {minutes != null
                    ? `${minutes} phút tới trường`
                    : "Chưa có thời gian di chuyển"}
                  {listing.geocode_confidence && listing.geocode_confidence !== "high"
                    ? " · vị trí tương đối"
                    : ""}
                </p>

                {selected && (
                  <Link
                    href={`/listings/${listing.id}`}
                    onClick={(e) => e.stopPropagation()}
                    className="mt-1 inline-block text-xs font-medium text-emerald-600 hover:underline"
                  >
                    Xem chi tiết →
                  </Link>
                )}
              </div>

              {cover ? (
                // eslint-disable-next-line @next/next/no-img-element
                <img
                  src={cover}
                  alt=""
                  className="h-20 w-20 shrink-0 rounded-lg object-cover"
                />
              ) : (
                <div className="grid h-20 w-20 shrink-0 place-items-center rounded-lg bg-slate-100 text-[10px] text-slate-400">
                  Không ảnh
                </div>
              )}
            </div>
          </li>
        );
      })}
    </ul>
  );
}
