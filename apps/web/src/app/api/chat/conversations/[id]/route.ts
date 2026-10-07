import { NextRequest, NextResponse } from "next/server";
import { apiFetch, type ApiError } from "@/lib/api";
import { withAccessToken } from "@/lib/authenticated-api";

export async function GET(req: NextRequest, { params }: { params: { id: string } }) {
  try {
    const query = req.nextUrl.searchParams.toString();
    const result = await withAccessToken(token => apiFetch<unknown>(`/chat/conversations/${encodeURIComponent(params.id)}?${query}`, {
      headers: { Authorization: `Bearer ${token}` }, cache: "no-store",
    }));
    return NextResponse.json(result, { headers: { "Cache-Control": "private, no-store" } });
  } catch (error) {
    const e = error as ApiError;
    return NextResponse.json({ detail: e.detail ?? "Không thể mở cuộc trò chuyện" }, { status: e.status ?? 500 });
  }
}

export async function DELETE(_req: NextRequest, { params }: { params: { id: string } }) {
  try {
    await withAccessToken(token => apiFetch<unknown>(`/chat/conversations/${encodeURIComponent(params.id)}`, {
      method: "DELETE", headers: { Authorization: `Bearer ${token}` },
    }));
    return new NextResponse(null, { status: 204 });
  } catch (error) {
    const e = error as ApiError;
    return NextResponse.json({ detail: e.detail ?? "Không thể xóa cuộc trò chuyện" }, { status: e.status ?? 500 });
  }
}
