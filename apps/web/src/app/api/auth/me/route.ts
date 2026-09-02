import { NextResponse } from "next/server";
import { getCurrentUser } from "@/lib/current-user";
import { clearAuthCookies } from "@/lib/session";

export async function GET() {
  const user = await getCurrentUser(true);
  if (!user) {
    // Cookie hỏng/hết hạn phải được xóa để middleware không hiểu nhầm rằng
    // khách vẫn còn phiên đăng nhập.
    clearAuthCookies();
    return NextResponse.json({ detail: "Phiên đăng nhập đã hết hạn" }, { status: 401 });
  }
  return NextResponse.json(user);
}
