// Helper format dữ liệu hiển thị — dùng chung cho listing card/detail/map.

export function formatPrice(price: number | null | undefined): string {
  if (price == null) return "Thỏa thuận";
  const trieu = price / 1_000_000;
  const formatted = Number.isInteger(trieu) ? trieu.toFixed(0) : trieu.toFixed(1);
  return `${formatted} triệu/tháng`;
}

export function formatArea(area: number | null | undefined): string {
  if (area == null) return "";
  return `${area} m²`;
}

export function formatDistance(meters: number | null | undefined): string {
  if (meters == null) return "";
  const km = meters / 1000;
  return `cách CTU ${km.toFixed(1)} km`;
}

export type RiskLevel = "safe" | "caution" | "suspicious" | "unknown";

export const RISK_BADGE: Record<RiskLevel, { label: string; className: string }> = {
  safe: { label: "An toàn", className: "bg-emerald-100 text-emerald-700" },
  caution: { label: "Cẩn trọng", className: "bg-amber-100 text-amber-700" },
  suspicious: { label: "Nghi vấn", className: "bg-rose-100 text-rose-700" },
  unknown: { label: "Chưa rõ", className: "bg-slate-100 text-slate-600" },
};

export function riskBadge(level: string): { label: string; className: string } {
  return RISK_BADGE[level as RiskLevel] ?? RISK_BADGE.unknown;
}
