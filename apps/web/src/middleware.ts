import { NextResponse, type NextRequest } from "next/server";
import { ACCESS_COOKIE, REFRESH_COOKIE } from "@/lib/config";

// Gate nhẹ theo sự tồn tại của cookie (không verify chữ ký ở đây — page tự
// gọi /me để xác thực thật). Middleware chỉ điều hướng UX: chặn vào trang cần
// login khi thiếu token, và đẩy user đã login khỏi trang login/register.
const PROTECTED = ["/me", "/dashboard"];
const AUTH_PAGES = ["/login", "/register"];

export function middleware(req: NextRequest) {
  const { pathname } = req.nextUrl;
  const hasSession =
    req.cookies.has(ACCESS_COOKIE) || req.cookies.has(REFRESH_COOKIE);

  if (PROTECTED.some((p) => pathname.startsWith(p)) && !hasSession) {
    const url = req.nextUrl.clone();
    url.pathname = "/login";
    url.searchParams.set("next", pathname);
    return NextResponse.redirect(url);
  }

  if (AUTH_PAGES.some((p) => pathname.startsWith(p)) && hasSession) {
    const url = req.nextUrl.clone();
    url.pathname = "/me";
    url.search = "";
    return NextResponse.redirect(url);
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/me/:path*", "/dashboard/:path*", "/login", "/register"],
};
