import { NextResponse } from "next/server";
import { moderateReport, type ApiError, type ModerationAction } from "@/lib/api";
import { getAccessToken } from "@/lib/session";

export async function PATCH(req: Request, { params }: { params: { id: string } }) {
  const token = getAccessToken();
  if (!token) {
    return NextResponse.json({ detail: "Chưa đăng nhập" }, { status: 401 });
  }
  let body: { action?: ModerationAction; note?: string | null };
  try {
    body = await req.json();
  } catch {
    return NextResponse.json({ detail: "Body không hợp lệ" }, { status: 400 });
  }
  if (!body.action) {
    return NextResponse.json({ detail: "Thiếu hành động kiểm duyệt" }, { status: 400 });
  }
  try {
    const result = await moderateReport(token, params.id, {
      action: body.action,
      note: body.note,
    });
    return NextResponse.json(result);
  } catch (error) {
    const err = error as ApiError;
    return NextResponse.json(
      { detail: err.detail ?? "Kiểm duyệt thất bại" },
      { status: err.status ?? 500 },
    );
  }
}
