import { NextResponse } from "next/server";
import { createReport, type ApiError, type ReportReason } from "@/lib/api";
import { getAccessToken } from "@/lib/session";

export async function POST(req: Request, { params }: { params: { id: string } }) {
  const token = getAccessToken();
  if (!token) {
    return NextResponse.json({ detail: "Chưa đăng nhập" }, { status: 401 });
  }
  let body: { reason?: ReportReason; note?: string | null };
  try {
    body = await req.json();
  } catch {
    return NextResponse.json({ detail: "Body không hợp lệ" }, { status: 400 });
  }
  if (!body.reason) {
    return NextResponse.json({ detail: "Vui lòng chọn lý do" }, { status: 400 });
  }
  try {
    const report = await createReport(token, params.id, {
      reason: body.reason,
      note: body.note,
    });
    return NextResponse.json(report, { status: 201 });
  } catch (error) {
    const err = error as ApiError;
    return NextResponse.json(
      { detail: err.detail ?? "Gửi báo cáo thất bại" },
      { status: err.status ?? 500 },
    );
  }
}
