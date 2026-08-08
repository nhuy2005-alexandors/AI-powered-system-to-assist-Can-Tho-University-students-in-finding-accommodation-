import { getNearby, type ApiError, type ListingOut } from "@/lib/api";
import MapShell from "./MapShell";

export const dynamic = "force-dynamic";

// Toạ độ ĐH Cần Thơ (khu II) — mặc định tâm tìm kiếm khi không có query.
// Khớp CAMPUSES[1] trong campuses.ts / apps/api/app/listings/routing.py:10.
const CTU_LAT = 10.0322;
const CTU_LNG = 105.7683;
const DEFAULT_RADIUS = 3000;

export default async function MapPage({
  searchParams,
}: {
  searchParams: { lat?: string; lng?: string; radius?: string };
}) {
  const lat = searchParams.lat ? Number(searchParams.lat) : CTU_LAT;
  const lng = searchParams.lng ? Number(searchParams.lng) : CTU_LNG;
  const radius = searchParams.radius ? Number(searchParams.radius) : DEFAULT_RADIUS;

  let items: ListingOut[];
  let errorMessage: string | null = null;
  try {
    items = await getNearby(lat, lng, radius);
  } catch (e) {
    errorMessage = (e as ApiError).detail ?? "Không thể tải danh sách tin lân cận";
    items = [];
  }

  return (
    <MapShell
      items={items}
      center={[lat, lng]}
      radius={radius}
      errorMessage={errorMessage}
    />
  );
}
