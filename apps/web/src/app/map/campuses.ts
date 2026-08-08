// Toạ độ 3 campus CTU — PHẢI khớp CAMPUSES trong apps/api/app/listings/routing.py:10
// theo cả thứ tự index (0=khu I, 1=khu II, 2=khu III) vì `route_time_campus[i]`
// từ API được tra bằng chính index này. Nguồn chốt: docs/specs/Map_Routing.md bảng Campus.
export const CAMPUSES = [
  { label: "Khu I", lat: 10.0159, lng: 105.7656 },
  { label: "Khu II", lat: 10.0322, lng: 105.7683 },
  { label: "Khu III", lat: 10.034, lng: 105.7798 },
] as const;

export const CAMPUS_LABELS = CAMPUSES.map((c) => c.label);
