import Link from "next/link";
import { getNearby, type ApiError, type ListingOut } from "@/lib/api";
import MapView from "./MapView";

export const dynamic = "force-dynamic";

// Toạ độ ĐH Cần Thơ (khu II) — mặc định tâm tìm kiếm khi không có query.
const CTU_LAT = 10.03;
const CTU_LNG = 105.769;
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
    <main className="min-h-screen bg-slate-50 p-4 sm:p-8">
      <div className="mx-auto max-w-3xl">
        <Link href="/" className="text-sm text-emerald-600 hover:text-emerald-700">
          ← Về danh sách
        </Link>

        <h1 className="mt-4 text-2xl font-bold text-slate-800">Tin gần bạn</h1>
        <p className="mt-1 text-sm text-slate-500">
          Bán kính tìm kiếm: {(radius / 1000).toFixed(1)} km quanh ĐH Cần Thơ.
        </p>

        {errorMessage && (
          <p className="mt-6 rounded-md bg-rose-50 px-3 py-2 text-sm text-rose-600">
            {errorMessage}
          </p>
        )}

        {!errorMessage && items.length === 0 && (
          <p className="mt-10 text-center text-slate-500">
            Không tìm thấy tin nào trong bán kính này
          </p>
        )}

        <div className="mt-6">
          <MapView items={items} center={[lat, lng]} />
        </div>
      </div>
    </main>
  );
}
