"use client";

import dynamic from "next/dynamic";
import type { ListingOut } from "@/lib/api";

// react-leaflet dùng window/document ngay khi import → phải tắt SSR, nếu
// không build Next sẽ lỗi "window is not defined" lúc render phía server.
const MapInner = dynamic(() => import("./MapInner"), {
  ssr: false,
  loading: () => (
    <div className="flex h-[70vh] w-full items-center justify-center rounded-lg bg-slate-100 text-sm text-slate-400">
      Đang tải bản đồ...
    </div>
  ),
});

export default function MapView({
  items,
  center,
}: {
  items: ListingOut[];
  center: [number, number];
}) {
  return <MapInner items={items} center={center} />;
}
