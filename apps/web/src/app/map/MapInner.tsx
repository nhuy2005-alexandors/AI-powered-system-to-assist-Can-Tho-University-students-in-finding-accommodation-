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
import {
  createCampusIcon,
  createHousingIcon,
  focusSelectedPosition,
  observeMapResize,
} from "@/lib/map-ui";
import { CAMPUSES } from "./campuses";
import type { MapViewProps } from "./MapView";

const PIN = createHousingIcon(L, false);
const PIN_SELECTED = createHousingIcon(L, true);
const CAMPUS_ICON = createCampusIcon(L);

// Bay tới tin được chọn (từ panel trái hoặc từ map) — giữ zoom hiện tại nếu đã đủ gần.
function FlyToSelected({
  target,
}: {
  target: [number, number] | null;
}) {
  const map = useMap();
  useEffect(() => {
    focusSelectedPosition(map, target);
  }, [target, map]);
  return null;
}

// Leaflet tính sai kích thước khi container đổi bề rộng (thu/mở panel trái) →
// gọi invalidateSize sau transition, nếu không map bị xám nửa bên.
function ResizeOnLayout() {
  const map = useMap();
  useEffect(() => observeMapResize(map), [map]);
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
