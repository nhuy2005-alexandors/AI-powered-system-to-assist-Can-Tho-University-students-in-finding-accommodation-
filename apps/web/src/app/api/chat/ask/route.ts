import { NextRequest, NextResponse } from "next/server";
import { apiFetch, type ApiError } from "@/lib/api";

export async function POST(req: NextRequest) {
  const body = await req.json();
  try {
    const result = await apiFetch<unknown>("/chat/ask", {
      method: "POST",
      body: JSON.stringify(body),
    });
    return NextResponse.json(result);
  } catch (error) {
    const apiError = error as ApiError;
    return NextResponse.json(
      { detail: apiError.detail ?? "Không thể gửi câu hỏi" },
      { status: apiError.status ?? 500 },
    );
  }
}
