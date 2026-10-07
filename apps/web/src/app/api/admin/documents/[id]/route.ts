import { NextRequest, NextResponse } from "next/server";
import { apiFetch, type ApiError } from "@/lib/api";
import { withAccessToken } from "@/lib/authenticated-api";

async function forward(req: NextRequest, id: string, method: "GET" | "PATCH") {
  let body: string | undefined;
  if (method === "PATCH") {
    try { body = JSON.stringify(await req.json()); }
    catch { return NextResponse.json({ detail: "Dữ liệu không hợp lệ" }, { status: 400 }); }
  }
  try {
    const result = await withAccessToken(token => apiFetch<unknown>(`/admin/documents/${encodeURIComponent(id)}?${req.nextUrl.searchParams}`, {
      method, body, headers: { Authorization: `Bearer ${token}` },
    }));
    return NextResponse.json(result, { headers: { "Cache-Control": "private, no-store" } });
  } catch (error) {
    const e = error as ApiError;
    return NextResponse.json({ detail: e.detail ?? "Không thể xử lý tài liệu" }, { status: e.status ?? 500 });
  }
}

export const GET = (req: NextRequest, { params }: { params: { id: string } }) => forward(req, params.id, "GET");
export const PATCH = (req: NextRequest, { params }: { params: { id: string } }) => forward(req, params.id, "PATCH");
