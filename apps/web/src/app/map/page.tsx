import { getNearby, type ApiError, type ListingOut } from "@/lib/api";
import SiteHeader from "../SiteHeader";
import MapScreen from "./MapScreen";

export const dynamic = "force-dynamic";

// Tâm tìm kiếm = CTU khu II, khớp CAMPUSES[1] backend (apps/api/app/listings/routing.py).
const CTU_LAT = 10.0322;
const CTU_LNG = 105.7683;
const DEFAULT_RADIUS = 3000;
const MIN_RADIUS = 500;
const MAX_RADIUS = 5000;

export default async function MapPage({
  searchParams,
}: {
  searchParams: { radius?: string };
}) {
  const parsed = Number(searchParams.radius);
  const radius = Number.isFinite(parsed)
    ? Math.min(MAX_RADIUS, Math.max(MIN_RADIUS, parsed))
    : DEFAULT_RADIUS;

  let items: ListingOut[] = [];
  let errorMessage: string | null = null;
  try {
    items = await getNearby(CTU_LAT, CTU_LNG, radius);
  } catch (e) {
    errorMessage = (e as ApiError).detail ?? "Không thể tải danh sách tin lân cận";
  }

  return (
    <div className="flex h-screen flex-col bg-paper">
      <SiteHeader />
      <MapScreen items={items} radius={radius} error={errorMessage} />
    </div>
  );
}
