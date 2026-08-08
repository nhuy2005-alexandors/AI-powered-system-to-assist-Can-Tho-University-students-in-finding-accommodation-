"use client";

import Link from "next/link";
import { useEffect } from "react";
import {
  MapContainer,
  Marker,
  Polyline,
  Popup,
  TileLayer,
  ZoomControl,
  useMap,
} from "react-leaflet";
import MarkerClusterGroup from "react-leaflet-cluster";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import type { ListingOut } from "@/lib/api";
import { formatPrice } from "@/lib/format";
import { CAMPUSES } from "./campuses";
import type { MapViewProps } from "./MapView";

// Pin dạng giọt nước như POI Google Maps. Dùng divIcon (không CircleMarker) vì
// markercluster chỉ gộp được L.Marker.
function pinIcon(color: string, size: number, ring: boolean) {
  const h = Math.round(size * 1.3);
  return L.divIcon({
    className: "",
    html: `<svg width="${size}" height="${h}" viewBox="0 0 24 32" xmlns="http://www.w3.org/2000/svg">
      <path d="M12 0C5.4 0 0 5.4 0 12c0 8.4 12 20 12 20s12-11.6 12-20C24 5.4 18.6 0 12 0z"
        fill="${color}" stroke="${ring ? "#ffffff" : "rgba(0,0,0,.15)"}" stroke-width="${ring ? 2.5 : 1}"/>
      <circle cx="12" cy="12" r="4.2" fill="#ffffff"/>
    </svg>`,
    iconSize: [size, h],
    iconAnchor: [size / 2, h],
    popupAnchor: [0, -h + 4],
  });
}

const PIN = pinIcon("#e11d48", 22, false);
const PIN_SELECTED = pinIcon("#0f766e", 32, true);

// Sao vàng cho campus CTU — mốc tham chiếu, phân biệt rõ với pin tin trọ.
const CAMPUS_ICON = L.divIcon({
  className: "",
  html: `<svg width="26" height="26" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
    <circle cx="12" cy="12" r="11" fill="#1d4ed8" stroke="#ffffff" stroke-width="2"/>
    <path d="M12 6l1.8 3.9 4.2.5-3.1 2.9.8 4.2L12 15.4 8.3 17.5l.8-4.2L6 10.4l4.2-.5z" fill="#fde047"/>
  </svg>`,
  iconSize: [26, 26],
  iconAnchor: [13, 13],
});

// Bay tới tin được chọn (từ panel trái hoặc từ map) — giữ zoom hiện tại nếu đã đủ gần.
function FlyToSelected({
  target,
}: {
  target: [number, number] | null;
}) {
  const map = useMap();
  useEffect(() => {
    if (!target) return;
    map.flyTo(target, Math.max(map.getZoom(), 16), { duration: 0.6 });
  }, [target, map]);
  return null;
}

// Leaflet tính sai kích thước khi container đổi bề rộng (thu/mở panel trái) →
// gọi invalidateSize sau transition, nếu không map bị xám nửa bên.
function ResizeOnLayout() {
  const map = useMap();
  useEffect(() => {
    const el = map.getContainer();
    const ro = new ResizeObserver(() => map.invalidateSize());
    ro.observe(el);
    return () => ro.disconnect();
  }, [map]);
  return null;
}

export default function MapInner({
  items,
  center,
  campus,
  selectedId,
  route,
  onSelect,
}: MapViewProps) {
  const withCoords = items.filter(
    (l): l is ListingOut & { lat: number; lng: number } =>
      l.lat != null && l.lng != null,
  );

  const selected = withCoords.find((l) => l.id === selectedId) ?? null;

  return (
    <MapContainer
      center={center}
      zoom={14}
      scrollWheelZoom
      zoomControl={false}
      className="h-full w-full"
    >
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />

      {/* Nút zoom góc dưới-phải (mặc định leaflet là trên-trái, sẽ đè lên panel/header) */}
      <ZoomControl position="bottomright" />

      <ResizeOnLayout />
      <FlyToSelected target={selected ? [selected.lat, selected.lng] : null} />

      {route && (
        <Polyline positions={route} pathOptions={{ color: "#1d4ed8", weight: 5, opacity: 0.85 }} />
      )}

      {CAMPUSES.map((c, i) => (
        <Marker key={c.label} position={[c.lat, c.lng]} icon={CAMPUS_ICON} zIndexOffset={500}>
          <Popup>
            <p className="font-medium text-slate-800">ĐH Cần Thơ · {c.label}</p>
            {i === campus && (
              <p className="text-xs text-emerald-700">Đang tính thời gian tới đây</p>
            )}
          </Popup>
        </Marker>
      ))}

      <MarkerClusterGroup chunkedLoading>
        {withCoords.map((listing) => {
          const minutes = listing.route_time_campus?.[campus] ?? null;
          const isSelected = listing.id === selectedId;
          return (
            <Marker
              key={listing.id}
              position={[listing.lat, listing.lng]}
              icon={isSelected ? PIN_SELECTED : PIN}
              zIndexOffset={isSelected ? 1000 : 0}
              eventHandlers={{ click: () => onSelect(listing.id) }}
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
                <Link
                  href={`/listings/${listing.id}`}
                  className="text-emerald-600 hover:underline"
                >
                  Xem chi tiết
                </Link>
              </Popup>
            </Marker>
          );
        })}
      </MarkerClusterGroup>
    </MapContainer>
  );
}
