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
