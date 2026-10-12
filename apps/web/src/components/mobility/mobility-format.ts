import type {
  NearbyStatus,
  RouteStatus,
  TravelMode,
} from "@/lib/mobility-contracts";

export const TRAVEL_MODES: { value: TravelMode; label: string }[] = [
  { value: "MOTORBIKE", label: "Xe máy" },
  { value: "WALK", label: "Đi bộ" },
  { value: "BICYCLE", label: "Xe đạp" },
  { value: "BUS", label: "Xe buýt" },
];

export const PLACE_CATEGORIES = [
  { value: "grocery", label: "Tạp hóa" },
  { value: "market", label: "Chợ" },
  { value: "pharmacy", label: "Nhà thuốc" },
  { value: "healthcare", label: "Cơ sở y tế" },
  { value: "police", label: "Công an" },
  { value: "bus_stop", label: "Trạm xe buýt" },
] as const;

export function routeStatusLabel(status: RouteStatus): string {
  const labels: Record<RouteStatus, string> = {
    NOT_CONFIGURED: "Dịch vụ chỉ đường chưa được cấu hình.",
    CAPABILITY_UNVERIFIED: "Khả năng phục vụ chế độ này chưa được xác minh.",
    UNSUPPORTED_MODE: "Chế độ này hiện chưa được hỗ trợ.",
    LOCATION_UNAVAILABLE: "Tin đăng chưa có vị trí để tính tuyến.",
    NO_ROUTE: "Không có tuyến phù hợp cho yêu cầu này.",
    RATE_LIMITED: "Dịch vụ đang giới hạn yêu cầu; hãy thử lại sau.",
    PROVIDER_ERROR: "Không thể tải tuyến lúc này.",
    OK: "Đã nhận kết quả tuyến.",
  };
  return labels[status];
}

export function nearbyStatusLabel(status: NearbyStatus): string {
  const labels: Record<NearbyStatus, string> = {
    NOT_CONFIGURED: "Dịch vụ tiện ích chưa được cấu hình.",
    CAPABILITY_UNVERIFIED: "Khả năng tìm nhóm tiện ích này chưa được xác minh.",
    UNSUPPORTED_CATEGORY: "Có nhóm tiện ích chưa được hỗ trợ.",
    LOCATION_UNAVAILABLE: "Tin đăng chưa có vị trí để tìm tiện ích.",
    EMPTY: "Không ghi nhận tiện ích nào trong phản hồi này.",
    RATE_LIMITED: "Dịch vụ đang giới hạn yêu cầu; hãy thử lại sau.",
    PROVIDER_ERROR: "Không thể tải tiện ích lúc này.",
    OK: "Đã nhận danh sách tiện ích.",
  };
  return labels[status];
}

export function formatDuration(seconds: number): string {
  const minutes = Math.round(seconds / 60);
  return `${minutes} phút`;
}

export function formatDistance(meters: number): string {
  return meters >= 1000
    ? `${(meters / 1000).toLocaleString("vi-VN", { maximumFractionDigits: 1 })} km`
    : `${Math.round(meters)} m`;
}

export function formatPrice(price: number | null): string {
  return price == null
    ? "Giá chưa rõ"
    : `${new Intl.NumberFormat("vi-VN").format(price)} đ/tháng`;
}

export function safeHttpUrl(value: string | null): string | null {
  if (!value) return null;
  try {
    const url = new URL(value);
    return url.protocol === "http:" || url.protocol === "https:"
      ? url.toString()
      : null;
  } catch {
    return null;
  }
}

export function localDateTimeInput(value: Date): string {
  const pad = (part: number) => String(part).padStart(2, "0");
  return `${value.getFullYear()}-${pad(value.getMonth() + 1)}-${pad(value.getDate())}T${pad(value.getHours())}:${pad(value.getMinutes())}`;
}

export function localDateTimeWithOffset(value: string): string | null {
  const match = /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})$/.exec(value);
  if (!match) return null;
  const [, year, month, day, hour, minute] = match;
  const localDate = new Date(
    Number(year),
    Number(month) - 1,
    Number(day),
    Number(hour),
    Number(minute),
  );
  if (
    localDate.getFullYear() !== Number(year) ||
    localDate.getMonth() !== Number(month) - 1 ||
    localDate.getDate() !== Number(day) ||
    localDate.getHours() !== Number(hour) ||
    localDate.getMinutes() !== Number(minute)
  ) {
    return null;
  }
  const offset = -localDate.getTimezoneOffset();
  const sign = offset >= 0 ? "+" : "-";
  const absOffset = Math.abs(offset);
  const offsetText = `${sign}${String(Math.floor(absOffset / 60)).padStart(2, "0")}:${String(absOffset % 60).padStart(2, "0")}`;
  return `${value}:00${offsetText}`;
}
