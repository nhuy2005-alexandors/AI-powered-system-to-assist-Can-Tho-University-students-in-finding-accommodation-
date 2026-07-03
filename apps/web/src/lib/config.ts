// Server-side config. API_INTERNAL_URL dùng cho fetch trong docker network
// (browser không chạm được `api:8000`); fallback localhost khi chạy ngoài docker.
export const API_URL =
  process.env.API_INTERNAL_URL ?? process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export const ACCESS_COOKIE = "access_token";
export const REFRESH_COOKIE = "refresh_token";

// TTL khớp backend (config.py: access 15min, refresh 30 ngày).
export const ACCESS_MAX_AGE = 15 * 60;
export const REFRESH_MAX_AGE = 30 * 24 * 60 * 60;
