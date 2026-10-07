import { NextRequest, NextResponse } from "next/server";
import { apiFetch, type ApiError } from "@/lib/api";
import { withAccessToken } from "@/lib/authenticated-api";

export async function GET(req: NextRequest) {
  try {
    const result = await withAccessToken(token => apiFetch<unknown>(`/admin/documents?${req.nextUrl.searchParams}`, {
      headers: { Authorization: `Bearer ${token}` },
    }));
    return NextResponse.json(result, { headers: { "Cache-Control": "private, no-store" } });
  } catch (error) {
    const e = error as ApiError;
    return NextResponse.json({ detail: e.detail ?? "Không thể tải tài liệu" }, { status: e.status ?? 500 });
  }
}
