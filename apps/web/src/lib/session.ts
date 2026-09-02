import { cookies } from "next/headers";
import {
  ACCESS_COOKIE,
  ACCESS_MAX_AGE,
  REFRESH_COOKIE,
  REFRESH_MAX_AGE,
} from "./config";

// httpOnly cookie — JS client không đọc được token (chống XSS đánh cắp token).
// Docker local vẫn chạy Next ở NODE_ENV=production nhưng dùng http://localhost,
// nên Secure phải là cấu hình triển khai thay vì suy ra từ NODE_ENV.
const cookieSecure = process.env.AUTH_COOKIE_SECURE === "true";

const baseOpts = {
  httpOnly: true,
  sameSite: "lax" as const,
  secure: cookieSecure,
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
