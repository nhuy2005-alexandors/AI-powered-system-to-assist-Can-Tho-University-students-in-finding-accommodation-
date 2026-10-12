import { NextResponse } from "next/server";
import { moderateReview, type ApiError } from "@/lib/api";
import { withAccessToken } from "@/lib/authenticated-api";

export async function PATCH(req: Request, { params }: { params: { id: string } }) {
  let body;
  try { body = await req.json(); }
  catch { return NextResponse.json({ detail: "Body không hợp lệ" }, { status: 400 }); }
  if (!body || !["approve", "hide"].includes(body.action)) {
    return NextResponse.json({ detail: "Thao tác không hợp lệ" }, { status: 400 });
  }
  try {
    return NextResponse.json(await withAccessToken((token) => moderateReview(token, params.id, body.action)));
  } catch (error) {
    const err = error as ApiError;
    return NextResponse.json({ detail: err.detail || "Không duyệt được đánh giá" }, { status: err.status || 502 });
  }
}
