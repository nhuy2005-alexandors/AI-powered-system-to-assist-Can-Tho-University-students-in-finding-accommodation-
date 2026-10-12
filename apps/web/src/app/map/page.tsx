import { getKtxCatalog, getNearby, type ApiError, type ListingOut } from "@/lib/api";
import type { KtxDormitory } from "@/lib/ktx";
import SiteHeader from "../SiteHeader";
import MapScreen from "./MapScreen";

export const dynamic = "force-dynamic";

// Tâm tìm kiếm = CTU khu II, khớp CAMPUSES[1] backend (apps/api/app/listings/routing.py).
const CTU_LAT = 10.0322;
const CTU_LNG = 105.7683;
const DEFAULT_RADIUS = 3000;
const MIN_RADIUS = 500;
const MAX_RADIUS = 5000;
const HOUSING_VALUES = ["phong_tro", "nha_mini"];

export default async function MapPage({
  searchParams,
}: {
  searchParams: { radius?: string; housing?: string; focus?: string; campus?: string; dormitory?: string };
}) {
  const parsed = Number(searchParams.radius);
  const radius = Number.isFinite(parsed)
    ? Math.min(MAX_RADIUS, Math.max(MIN_RADIUS, parsed))
    : DEFAULT_RADIUS;
  const housing = HOUSING_VALUES.includes(searchParams.housing ?? "") ? searchParams.housing! : "";
  const campus = ["0", "1", "2"].includes(searchParams.campus ?? "") ? Number(searchParams.campus) : 1;

  const initialDormitory = ["A", "B"].includes(searchParams.dormitory ?? "") ? searchParams.dormitory as "A" | "B" : null;
  let dormitories: KtxDormitory[] = [];
  let dormitoryError: string | null = null;
  const dormitoryLoad = getKtxCatalog().then(data => { dormitories = data.dormitories; }).catch(() => { dormitoryError = "Chưa tải được vị trí KTX. Vui lòng thử lại sau."; });
  let items: ListingOut[] = [];
  let errorMessage: string | null = null;
  try {
    // Bỏ mô tả + ảnh thứ 2 trở đi trước khi đưa xuống client: bản đồ chỉ dùng ảnh bìa, ~700 tin
    // đủ field làm trang nặng 1,9 MB (đo 07/10).
    items = (await getNearby(CTU_LAT, CTU_LNG, radius, housing || undefined)).map((l) => ({
      ...l,
      description: null,
      images: l.images.slice(0, 1),
    }));
  } catch (e) {
    errorMessage = (e as ApiError).detail ?? "Không thể tải danh sách tin lân cận";
  }

  await dormitoryLoad;

  return (
    <div className="flex h-screen flex-col bg-paper">
      <SiteHeader />
      <MapScreen
        items={items}
        dormitories={dormitories}
        dormitoryError={dormitoryError}
        initialDormitory={initialDormitory}
        radius={radius}
        housing={housing}
        error={errorMessage}
        focusId={Number.isFinite(Number(searchParams.focus)) ? Number(searchParams.focus) : null}
        initialCampus={campus}
      />
    </div>
  );
}
