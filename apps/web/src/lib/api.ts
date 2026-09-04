import { API_URL } from "./config";

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
  posted_by: number | null;
  risk_score: number | null;
  risk_reasons: string[];
  risk_level: string;
  geocode_confidence: string | null;
  freshness_score: number | null;
  freshness_label: string;
  quality_score: number | null;
  last_seen: string | null;
  route_time_campus: number[] | null; // [khuI, khuII, khuIII] phút, null = chưa route
  report_count: number;
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

export function getNearby(lat: number, lng: number, radius: number): Promise<ListingOut[]> {
  return apiFetch<ListingOut[]>(`/listings/nearby${buildQuery({ lat, lng, radius })}`);
}

// campus: 0=khu I, 1=khu II, 2=khu III. Trả polyline [lat,lng] campus→tin (FR-M.8).
export function getListingRoute(id: number | string, campus: number): Promise<number[][]> {
  return apiFetch<number[][]>(`/listings/${id}/route${buildQuery({ campus })}`);
}

export function getMyListings(token: string): Promise<ListingOut[]> {
  return apiFetch<ListingOut[]>("/listings/mine", {
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
  params: { q?: string; status?: AdminListingStatus; page?: number; size?: number } = {},
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
