import { NextResponse } from "next/server";
import { register, type ApiError } from "@/lib/api";
import { setAuthCookies } from "@/lib/session";

export async function POST(req: Request) {
  let body: { email?: string; password?: string; name?: string };
  try {
    body = await req.json();
  } catch {
    return NextResponse.json({ detail: "Body không hợp lệ" }, { status: 400 });
  }

  const { email, password, name } = body;
  if (!email || !password) {
    return NextResponse.json({ detail: "Thiếu email hoặc mật khẩu" }, { status: 400 });
  }
  if (password.length < 8) {
    return NextResponse.json({ detail: "Mật khẩu tối thiểu 8 ký tự" }, { status: 400 });
  }

  try {
    const tokens = await register(email, password, name);
    setAuthCookies(tokens.access_token, tokens.refresh_token);
    return NextResponse.json({ ok: true });
  } catch (e) {
    const err = e as ApiError;
    return NextResponse.json(
      { detail: err.detail ?? "Đăng ký thất bại" },
      { status: err.status ?? 500 },
    );
  }
}
