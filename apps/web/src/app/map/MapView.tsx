"use client";

import dynamic from "next/dynamic";
import type { ListingOut } from "@/lib/api";

// react-leaflet dùng window/document ngay khi import → phải tắt SSR, nếu
// không build Next sẽ lỗi "window is not defined" lúc render phía server.
const MapInner = dynamic(() => import("./MapInner"), {
  ssr: false,
  loading: () => (
    <div className="flex h-full w-full items-center justify-center bg-slate-100 text-sm text-slate-400">
      Đang tải bản đồ...
    </div>
  ),
});

export type MapViewProps = {
  items: ListingOut[];
  center: [number, number];
  campus: number;
  selectedId: number | null;
  route: [number, number][] | null;
  onSelect: (id: number) => void;
};

export default function MapView(props: MapViewProps) {
  return <MapInner {...props} />;
}
