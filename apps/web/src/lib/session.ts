import { cookies } from "next/headers";
import {
  ACCESS_COOKIE,
  ACCESS_MAX_AGE,
  REFRESH_COOKIE,
  REFRESH_MAX_AGE,
} from "./config";

// httpOnly cookie — JS client không đọc được token (chống XSS đánh cắp token).
// secure=false ở dev (http localhost); prod bật qua NODE_ENV.
const isProd = process.env.NODE_ENV === "production";

const baseOpts = {
  httpOnly: true,
  sameSite: "lax" as const,
  secure: isProd,
  path: "/",
};

export function setAuthCookies(access: string, refresh: string): void {
  const jar = cookies();
  jar.set(ACCESS_COOKIE, access, { ...baseOpts, maxAge: ACCESS_MAX_AGE });
  jar.set(REFRESH_COOKIE, refresh, { ...baseOpts, maxAge: REFRESH_MAX_AGE });
}

export function clearAuthCookies(): void {
  const jar = cookies();
  jar.delete(ACCESS_COOKIE);
  jar.delete(REFRESH_COOKIE);
}

export function getAccessToken(): string | undefined {
  return cookies().get(ACCESS_COOKIE)?.value;
}

export function getRefreshToken(): string | undefined {
  return cookies().get(REFRESH_COOKIE)?.value;
}
