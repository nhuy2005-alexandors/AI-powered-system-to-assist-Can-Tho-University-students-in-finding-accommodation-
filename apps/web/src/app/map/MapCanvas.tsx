"use client";

import { useEffect, useMemo } from "react";
import { Circle, MapContainer, Marker, Polyline, TileLayer, useMap } from "react-leaflet";
import MarkerClusterGroup from "react-leaflet-cluster";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import type { ListingWithCoords } from "./MapScreen";

// Toạ độ 3 khu CTU — khớp CAMPUSES backend (apps/api/app/listings/routing.py).
const CAMPUSES: [number, number][] = [
  [10.0159, 105.7656], // khu I
  [10.0322, 105.7683], // khu II
  [10.034, 105.7798], // khu III
];
const CAMPUS_MARKER_LABELS = ["CTU khu I", "CTU khu II", "CTU khu III"];

// Chấm tròn xanh 15px viền trắng theo mockup 03; tin đang chọn: to hơn + navy.
function dotIcon(selected: boolean): L.DivIcon {
  const size = selected ? 21 : 15;
  const bg = selected ? "#06305c" : "#1069bd";
  return L.divIcon({
    className: "",
    html: `<span style="display:block;width:${size}px;height:${size}px;border-radius:9999px;background:${bg};border:3px solid #fff;box-shadow:0 2px 6px rgba(0,0,0,.3)"></span>`,
    iconSize: [size, size],
    iconAnchor: [size / 2, size / 2],
  });
}

// Campus: ô vuông navy + nhãn trắng bên dưới (mockup 03). Outer dịch -50%+11px
// để tâm ô vuông trùng toạ độ dù nhãn rộng hơn ô.
function campusIcon(label: string): L.DivIcon {
  return L.divIcon({
    className: "",
    html:
      '<div style="display:flex;flex-direction:column;align-items:center;gap:5px;width:max-content;transform:translateX(calc(-50% + 11px))">' +
      '<span style="display:block;width:22px;height:22px;background:#06305c;border:3px solid #fff;box-shadow:0 3px 8px rgba(0,0,0,.3)"></span>' +
      `<span style="font-size:12.5px;font-weight:700;color:#06305c;background:rgba(255,255,255,.92);padding:3px 8px;border-radius:7px;white-space:nowrap">${label}</span>` +
      "</div>",
    iconSize: [22, 22],
    iconAnchor: [11, 11],
  });
}

// Cluster: vòng tròn xanh + số tin, to dần theo số lượng (mockup 03).
function clusterIcon(cluster: { getChildCount(): number }): L.DivIcon {
  const count = cluster.getChildCount();
  const size = count < 10 ? 34 : count < 100 ? 40 : 46;
  return L.divIcon({
    className: "",
    html: `<div style="display:flex;align-items:center;justify-content:center;width:${size}px;height:${size}px;border-radius:9999px;background:rgba(16,105,189,.9);border:3px solid rgba(255,255,255,.85);color:#fff;font-weight:700;font-size:13px;box-shadow:0 4px 12px rgba(6,48,92,.35)">${count}</div>`,
    iconSize: [size, size],
    iconAnchor: [size / 2, size / 2],
  });
}

// Chọn tin từ danh sách bên trái → bay tới marker tương ứng.
function FlyToSelected({ selected }: { selected: ListingWithCoords | null }) {
  const map = useMap();
  useEffect(() => {
    if (selected) {
      map.flyTo([selected.lat, selected.lng], Math.max(map.getZoom(), 16), {
        duration: 0.6,
      });
    }
  }, [map, selected]);
  return null;
}

export default function MapCanvas({
  items,
  campus,
  radius,
  selectedId,
  route,
  onSelect,
}: {
  items: ListingWithCoords[];
  campus: number;
  radius: number;
  selectedId: number | null;
  route: [number, number][] | null;
  onSelect: (listing: ListingWithCoords) => void;
}) {
  const center = CAMPUSES[1]; // tâm tìm kiếm cố định = khu II, khớp map/page.tsx
  const selected = useMemo(
    () => items.find((l) => l.id === selectedId) ?? null,
    [items, selectedId],
  );

  return (
    <MapContainer center={center} zoom={14} scrollWheelZoom className="h-full w-full">
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />

      {/* Vòng bán kính tìm kiếm — nét đứt xanh theo mockup */}
      <Circle
        center={center}
        radius={radius}
        pathOptions={{ color: "#1069bd", opacity: 0.45, weight: 2, dashArray: "8 8", fill: false }}
      />

      <Marker
        position={CAMPUSES[campus]}
        icon={campusIcon(CAMPUS_MARKER_LABELS[campus])}
        zIndexOffset={500}
      />

      {route && <Polyline positions={route} pathOptions={{ color: "#1069bd", weight: 4 }} />}

      <MarkerClusterGroup
        chunkedLoading
        iconCreateFunction={clusterIcon}
        maxClusterRadius={60}
        showCoverageOnHover={false}
      >
        {items.map((listing) => (
          <Marker
            key={listing.id}
            position={[listing.lat, listing.lng]}
            icon={dotIcon(listing.id === selectedId)}
            zIndexOffset={listing.id === selectedId ? 400 : 0}
            eventHandlers={{ click: () => onSelect(listing) }}
          />
        ))}
      </MarkerClusterGroup>

      <FlyToSelected selected={selected} />
    </MapContainer>
  );
}
