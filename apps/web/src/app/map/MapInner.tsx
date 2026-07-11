"use client";

import Link from "next/link";
import { useState } from "react";
import { MapContainer, Marker, Polyline, Popup, TileLayer } from "react-leaflet";
import MarkerClusterGroup from "react-leaflet-cluster";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import { getListingRoute, type ListingOut } from "@/lib/api";
import { formatPrice } from "@/lib/format";

// Chấm xanh HTML thay CircleMarker — markercluster chỉ gộp được L.Marker, không gộp CircleMarker.
const dotIcon = L.divIcon({
  className: "",
  html: '<span style="display:block;width:16px;height:16px;border-radius:9999px;background:#10b981;border:2px solid #059669"></span>',
  iconSize: [16, 16],
  iconAnchor: [8, 8],
});

// Index khớp CAMPUSES trong apps/api/app/listings/routing.py (0=khu I,1=khu II,2=khu III).
const CAMPUS_LABELS = ["Khu I", "Khu II", "Khu III"];

export default function MapInner({
  items,
  center,
}: {
  items: ListingOut[];
  center: [number, number];
}) {
  const [campus, setCampus] = useState(1); // mặc định khu II (FR-M.3)
  const [route, setRoute] = useState<[number, number][] | null>(null);

  const withCoords = items.filter(
    (l): l is ListingOut & { lat: number; lng: number } => l.lat != null && l.lng != null,
  );

  async function showRoute(listingId: number) {
    try {
      const path = await getListingRoute(listingId, campus);
      setRoute(path as [number, number][]);
    } catch {
      // ORS chưa cấu hình / lỗi mạng — không vẽ đường, không chặn UI (FR-M.8 on-demand)
      setRoute(null);
    }
  }

  return (
    <div>
      <div className="mb-3 flex gap-2">
        {CAMPUS_LABELS.map((label, i) => (
          <button
            key={label}
            type="button"
            onClick={() => {
              setCampus(i);
              setRoute(null);
            }}
            className={`rounded-md px-3 py-1.5 text-sm font-medium transition ${
              campus === i
                ? "bg-emerald-600 text-white"
                : "bg-slate-100 text-slate-600 hover:bg-slate-200"
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      <MapContainer
        center={center}
        zoom={14}
        scrollWheelZoom
        className="h-[70vh] w-full rounded-lg"
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        {route && <Polyline positions={route} pathOptions={{ color: "#2563eb", weight: 4 }} />}
        <MarkerClusterGroup chunkedLoading>
        {withCoords.map((listing) => {
          const minutes = listing.route_time_campus?.[campus] ?? null;
          return (
            <Marker
              key={listing.id}
              position={[listing.lat, listing.lng]}
              icon={dotIcon}
              eventHandlers={{ click: () => showRoute(listing.id) }}
            >
              <Popup>
                <p className="font-medium text-slate-800">{listing.title}</p>
                <p className="font-semibold text-emerald-700">{formatPrice(listing.price)}</p>
                {listing.address && (
                  <p className="text-sm text-slate-600">{listing.address}</p>
                )}
                <p className="text-xs text-slate-400">
                  {minutes != null ? `${minutes} phút tới trường` : "Chưa có thời gian di chuyển"}
                  {listing.geocode_confidence && listing.geocode_confidence !== "high"
                    ? " · vị trí tương đối"
                    : ""}
                </p>
                <Link href={`/listings/${listing.id}`} className="text-emerald-600 hover:underline">
                  Xem chi tiết
                </Link>
              </Popup>
            </Marker>
          );
        })}
        </MarkerClusterGroup>
      </MapContainer>
    </div>
  );
}
