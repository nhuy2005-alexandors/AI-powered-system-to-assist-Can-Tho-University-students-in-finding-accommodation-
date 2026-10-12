import { API_URL } from "./config";
import type { KtxCatalog } from "./ktx";

export function getKtxCatalog(): Promise<KtxCatalog> {
  return apiFetch<KtxCatalog>("/ktx");
}

export type AdminReviewItem = ReviewOut & { listing_title: string };
export type AdminReviewList = { total: number; items: AdminReviewItem[] };

export function getFlaggedReviews(token: string, page = 1): Promise<AdminReviewList> {
  return apiFetch(`/admin/reviews/flagged?page=${page}&size=50`, {
    headers: { Authorization: `Bearer ${token}` },
  });
}

export function moderateReview(token: string, id: string, action: "approve" | "hide"): Promise<ReviewOut> {
  return apiFetch(`/admin/reviews/${id}`, {
    method: "PATCH",
    headers: { Authorization: `Bearer ${token}` },
    body: JSON.stringify({ action }),
  });
}

// ---- Star reviews + AI sentiment moderation ----

export type ReviewSentiment = "positive" | "neutral" | "negative";
export type ReviewModerationStatus = "published" | "flagged" | "hidden";

export type ReviewOut = {
  id: number;
  listing_id: number;
  user_id: number;
  author_name: string;
  author_avatar_url: string | null;
  rating: number;
  comment: string;
  sentiment_label: ReviewSentiment;
  negative_score: number;
  is_flagged: boolean;
  moderation_status: ReviewModerationStatus;
  model_version: string;
  created_at: string;
  updated_at: string;
};

export type ReviewList = {
  summary: {
    average_rating: number | null;
    total: number;
    rating_counts: Record<number, number>;
  };
  items: ReviewOut[];
};

export function getListingReviews(
  listingId: number | string,
  page = 1,
  size = 20,
): Promise<ReviewList> {
  return apiFetch<ReviewList>(
    `/listings/${listingId}/reviews${buildQuery({ page, size })}`,
  );
}

export function createReview(
  token: string,
  listingId: number | string,
  data: { rating: number; comment: string },
): Promise<ReviewOut> {
  return apiFetch<ReviewOut>(`/listings/${listingId}/reviews`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
    body: JSON.stringify(data),
  });
}


// ---- Community reports + Admin moderation ----

export type ReportReason = "wrong_price" | "expired" | "scam" | "other";
export type ReportStatus = "pending" | "reviewed" | "dismissed";
export type ModerationAction = "dismiss" | "flag" | "hide";

export type ReportOut = {
  id: number;
  listing_id: number;
  reporter_id: number | null;
  reason: ReportReason;
  note: string | null;
  status: ReportStatus;
  created_at: string;
  reviewed_by: number | null;
  reviewed_at: string | null;
  resolution_note: string | null;
};

export type AdminReportItem = ReportOut & {
  reporter_email: string | null;
  reporter_name: string | null;
  listing_title: string;
  listing_status: string;
  listing_price: number | null;
  listing_address: string | null;
  risk_score: number | null;
  risk_level: string;
  risk_reasons: string[];
  open_report_count: number;
};

export type AdminReportList = { total: number; items: AdminReportItem[] };

export type AdminDashboardSummary = {
  total_listings: number;
  active_listings: number;
  flagged_listings: number;
  hidden_listings: number;
  pending_reports: number;
  reporting_users: number;
  total_users: number;
};

export type AdminListingStatus = "active" | "expired" | "flagged" | "hidden";

export type AdminListingItem = {
  id: number;
  title: string;
  price: number | null;
  address: string | null;
  district: string | null;
  source: string;
  status: AdminListingStatus;
  risk_score: number | null;
  risk_level: string;
  risk_reasons: string[];
  report_count: number;
  posted_by: number | null;
  first_seen: string | null;
  last_seen: string | null;
};

export type AdminListingList = { total: number; items: AdminListingItem[] };

export type AdminUserItem = {
  id: number;
  email: string;
  name: string | null;
  role: string;
  email_verified: boolean;
  created_at: string;
  listing_count: number;
  report_count: number;
};

export type AdminUserList = { total: number; items: AdminUserItem[] };

export type ModerationResult = {
  listing_id: number;
  action: ModerationAction;
  resolved_reports: number;
  listing_status: string;
  risk_score: number | null;
  risk_level: string | null;
};

export function createReport(
  token: string,
  listingId: number | string,
  data: { reason: ReportReason; note?: string | null },
): Promise<ReportOut> {
  return apiFetch<ReportOut>(`/listings/${listingId}/report`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
    body: JSON.stringify(data),
  });
}

export function getAdminReports(
  token: string,
  status?: ReportStatus,
): Promise<AdminReportList> {
  const query = status ? `?status=${status}&size=100` : "?size=100";
  return apiFetch<AdminReportList>(`/admin/reports${query}`, {
    headers: { Authorization: `Bearer ${token}` },
  });
}

export function getAdminSummary(token: string): Promise<AdminDashboardSummary> {
  return apiFetch<AdminDashboardSummary>("/admin/summary", {
    headers: { Authorization: `Bearer ${token}` },
  });
}

export function moderateReport(
  token: string,
  reportId: number | string,
  data: { action: ModerationAction; note?: string | null },
): Promise<ModerationResult> {
  return apiFetch<ModerationResult>(`/admin/reports/${reportId}`, {
    method: "PATCH",
    headers: { Authorization: `Bearer ${token}` },
    body: JSON.stringify(data),
  });
}

export function getAdminListings(
  token: string,
  params: {
    q?: string;
    status?: AdminListingStatus;
    page?: number;
    size?: number;
  } = {},
): Promise<AdminListingList> {
  return apiFetch<AdminListingList>(
    `/admin/listings${buildQuery({
      q: params.q,
      status: params.status,
      page: params.page,
      size: params.size ?? 50,
    })}`,
    { headers: { Authorization: `Bearer ${token}` } },
  );
}

export function updateAdminListingStatus(
  token: string,
  listingId: number | string,
  status: AdminListingStatus,
): Promise<AdminListingItem> {
  return apiFetch<AdminListingItem>(`/admin/listings/${listingId}/status`, {
    method: "PATCH",
    headers: { Authorization: `Bearer ${token}` },
    body: JSON.stringify({ status }),
  });
}

export function getAdminUsers(
  token: string,
  params: { q?: string; page?: number; size?: number } = {},
): Promise<AdminUserList> {
  return apiFetch<AdminUserList>(
    `/admin/users${buildQuery({ q: params.q, page: params.page, size: params.size ?? 50 })}`,
    { headers: { Authorization: `Bearer ${token}` } },
  );
}



export type TokenPair = {
  access_token: string;
  refresh_token: string;
  token_type: string;
};

export type User = {
  id: number;
  email: string;
  name: string | null;
  role: string;
  avatar_url: string | null;
};

export type ApiError = { status: number; detail: string };

// Gọi FastAPI từ server (route handler / server component). KHÔNG dùng ở client.
export async function apiFetch<T>(
  path: string,
  init: RequestInit = {},
): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init.headers ?? {}) },
    cache: "no-store",
  });

  if (!res.ok) {
    let detail = `Lỗi ${res.status}`;
    try {
      const body = (await res.json()) as { detail?: string };
      if (body?.detail) detail = body.detail;
    } catch {
      // body không phải JSON — giữ message mặc định
    }
    throw { status: res.status, detail } satisfies ApiError;
  }

  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

export function login(email: string, password: string): Promise<TokenPair> {
  return apiFetch<TokenPair>("/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
}

// Tài khoản cấp trước cho buổi thử nghiệm chỉ có identity provider='ctu'
// (không có 'local') ⇒ phải đi đường riêng, /auth/login sẽ trả 401.
export function loginCtu(mssv: string, password: string): Promise<TokenPair> {
  return apiFetch<TokenPair>("/auth/login/ctu", {
    method: "POST",
    body: JSON.stringify({ mssv, password }),
  });
}

export function register(
  email: string,
  password: string,
  name?: string,
): Promise<TokenPair> {
  return apiFetch<TokenPair>("/auth/register", {
    method: "POST",
    body: JSON.stringify({ email, password, name: name || null }),
  });
}

export function refresh(refreshToken: string): Promise<TokenPair> {
  return apiFetch<TokenPair>("/auth/refresh", {
    method: "POST",
    body: JSON.stringify({ refresh_token: refreshToken }),
  });
}

export function getMe(accessToken: string): Promise<User> {
  return apiFetch<User>("/auth/me", {
    headers: { Authorization: `Bearer ${accessToken}` },
  });
}

// ---- Listings ----

export type ListingOut = {
  id: number;
  posted_by: number | null;
  status: string;
  title: string;
  price: number | null;
  area: number | null;
  address: string | null;
  district: string | null;
  lat: number | null;
  lng: number | null;
  distance_to_ctu: number | null;
  description: string | null;
  images: string[];
  source: string;
  source_url: string | null;
  risk_score: number | null;
  risk_level: string;
  geocode_confidence: string | null;
  freshness_score: number | null;
  freshness_label: string;
  quality_score: number | null;
  last_seen: string | null;
  route_time_campus: number[] | null; // [khuI, khuII, khuIII] phút, null = chưa route
  listing_type: string | null; // phong_tro | nha_mini | ...
  offer_kind: string | null; // "lease_transfer" = pass phòng / sang nhượng
  location_precise: boolean | null; // false = toạ độ cấp phường (điểm mặc định của sàn) → bản đồ ẩn mặc định
};

export type SearchResult = {
  total: number;
  page: number;
  size: number;
  items: ListingOut[];
};

export type SearchListingsParams = {
  q?: string;
  min_price?: number;
  max_price?: number;
  min_area?: number;
  district?: string;
  max_distance_ctu?: number;
  housing?: string; // phong_tro | nha_mini; bỏ trống = cả hai
  sort?: string;
  page?: number;
  size?: number;
};

export type ListingInput = {
  title: string;
  price?: number | null;
  area?: number | null;
  address?: string | null;
  district?: string | null;
  description?: string | null;
  images?: string[];
};

function buildQuery(params: Record<string, string | number | undefined>): string {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== null && value !== "") {
      search.set(key, String(value));
    }
  }
  const qs = search.toString();
  return qs ? `?${qs}` : "";
}

export function searchListings(params: SearchListingsParams): Promise<SearchResult> {
  return apiFetch<SearchResult>(`/listings${buildQuery(params)}`);
}

export function getListing(id: number | string): Promise<ListingOut> {
  return apiFetch<ListingOut>(`/listings/${id}`);
}

export function getNearby(
  lat: number,
  lng: number,
  radius: number,
  housing?: string,
): Promise<ListingOut[]> {
  return apiFetch<ListingOut[]>(`/listings/nearby${buildQuery({ lat, lng, radius, housing })}`);
}

// campus: 0=khu I, 1=khu II, 2=khu III. Trả polyline [lat,lng] campus→tin (FR-M.8).
export function getListingRoute(id: number | string, campus: number): Promise<number[][]> {
  return apiFetch<number[][]>(`/listings/${id}/route${buildQuery({ campus })}`);
}

// Liên hệ của 1 tin — endpoint riêng, chỉ gọi khi người dùng mở đúng tin đó.
export type ContactOut = {
  phone: string | null;
  zalo: string | null;
  facebook: string | null;
  source: string;
  source_url: string | null;
};

export function getListingContact(id: number | string): Promise<ContactOut> {
  return apiFetch<ContactOut>(`/listings/${id}/contact`);
}

// ---- Tiện ích OSM (apps/api/app/pois) ----

export type PoiOut = {
  id: number;
  category: string;
  name: string | null;
  lat: number;
  lng: number;
  distance_m: number; // đường chim bay
};

export type PoiSummary = {
  radius: number;
  categories: { category: string; label: string; count: number; nearest: PoiOut | null }[];
};

export function getPois(lat: number, lng: number, radius: number): Promise<PoiOut[]> {
  return apiFetch<PoiOut[]>(`/pois${buildQuery({ lat, lng, radius })}`);
}

export function getPoiSummary(lat: number, lng: number, radius: number): Promise<PoiSummary> {
  return apiFetch<PoiSummary>(`/pois/summary${buildQuery({ lat, lng, radius })}`);
}

// tin admin nhập tay (trang Quản lý nhà trọ) — sinh viên không đăng tin (ADR-024)
export function getManagedListings(token: string): Promise<ListingOut[]> {
  return apiFetch<ListingOut[]>("/listings/managed", {
    headers: { Authorization: `Bearer ${token}` },
  });
}

export function createListing(token: string, data: ListingInput): Promise<ListingOut> {
  return apiFetch<ListingOut>("/listings", {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
    body: JSON.stringify(data),
  });
}

export function updateListing(
  token: string,
  id: number | string,
  data: Partial<ListingInput>,
): Promise<ListingOut> {
  return apiFetch<ListingOut>(`/listings/${id}`, {
    method: "PUT",
    headers: { Authorization: `Bearer ${token}` },
    body: JSON.stringify(data),
  });
}

export function deleteListing(token: string, id: number | string): Promise<void> {
  return apiFetch<void>(`/listings/${id}`, {
    method: "DELETE",
    headers: { Authorization: `Bearer ${token}` },
  });
}
