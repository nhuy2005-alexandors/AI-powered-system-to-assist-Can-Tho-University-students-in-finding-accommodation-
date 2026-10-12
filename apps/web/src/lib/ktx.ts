export type KtxLocation = {
  lat: number; lng: number; source_url: string; source_name: string;
  precision: "representative"; verified_at: string; label: string;
};
export type KtxDormitory = {
  id: "A" | "B"; name: string; capacity: number; description: string;
  buildings: string; phone: string; cover: string; location: KtxLocation;
};
export type KtxRoomType = {
  id: string; code: string; area_ids: ("A" | "B")[]; capacities: number[];
  capacity_label: string; cooking_allowed: boolean | null;
  bed_type: "single" | "bunk" | "unknown"; bathroom: string | null;
  description: string; price: number;
  price_period: "unconfirmed" | "monthly" | "semester_3_5_months";
  source_id: string; notes: string;
};
export type KtxPhysicalRoom = {
  id: string; dormitory_id: "A" | "B"; building: string; number: string; room_type_id: string;
  capacity: number; status: "unknown" | "available" | "full" | "maintenance";
  available_beds: number | null; verified_at: string | null; notes: string;
};
export type KtxCatalog = {
  academic_year?: string | null; term?: string; rooms?: KtxPhysicalRoom[];
  version: string; updated_at: string; address: string; email: string;
  registration_url: string;
  sources: { id: string; title: string; url: string | null; year: number | null; note: string }[];
  dormitories: KtxDormitory[]; room_types: KtxRoomType[];
  facts: { id: string; title: string; content: string; source_id: string; tags: string[] }[];
  images: { src: string; alt: string; dormitory_id: "A" | "B"; source_url: string; original_url: string; credit: string; sha256: string; bytes: number; room_id?: string | null; room_type_id?: string | null }[];
};

export function ktxMapUrl(area: KtxDormitory) {
  return "/map?campus=1&radius=1000&dormitory=" + area.id;
}
export function ktxDirectionsUrl(area: KtxDormitory) {
  return "https://www.google.com/maps/dir/?api=1&destination=" + area.location.lat + "," + area.location.lng;
}
export function ktxPricePeriod(room: KtxRoomType, academicYear?: string | null) {
  if (room.price_period === "monthly") return "/ người / tháng";
  return room.price_period === "semester_3_5_months"
    ? "/ người / học kỳ 3,5 tháng" + (academicYear ? ` (${academicYear.split("-")[0]})` : "")
    : "/ người · chưa xác nhận kỳ tính giá";
}
