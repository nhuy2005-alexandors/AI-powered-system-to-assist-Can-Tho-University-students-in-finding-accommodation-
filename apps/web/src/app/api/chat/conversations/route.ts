import { NextRequest, NextResponse } from "next/server";
import { apiFetch, type ApiError } from "@/lib/api";
import { withAccessToken } from "@/lib/authenticated-api";

export async function GET(req: NextRequest) {
  try {
    const query = req.nextUrl.searchParams.toString();
    const result = await withAccessToken(token => apiFetch<unknown>(`/chat/conversations?${query}`, {
      headers: { Authorization: `Bearer ${token}` }, cache: "no-store",
    }));
    return NextResponse.json(result, { headers: { "Cache-Control": "private, no-store" } });
  } catch (error) {
    const e = error as ApiError;
    return NextResponse.json({ detail: e.detail ?? "Không thể tải lịch sử" }, { status: e.status ?? 500 });
  }
}
