import { NextResponse } from "next/server";
import { createListing, type ApiError, type ListingInput } from "@/lib/api";
import { getAccessToken } from "@/lib/session";

export async function POST(req: Request) {
  const token = getAccessToken();
  if (!token) {
    return NextResponse.json({ detail: "Chưa đăng nhập" }, { status: 401 });
  }

  let body: Partial<ListingInput>;
  try {
    body = await req.json();
  } catch {
    return NextResponse.json({ detail: "Body không hợp lệ" }, { status: 400 });
  }

  if (!body.title) {
    return NextResponse.json({ detail: "Thiếu tiêu đề" }, { status: 400 });
  }

  try {
    const listing = await createListing(token, body as ListingInput);
    return NextResponse.json(listing, { status: 201 });
  } catch (e) {
    const err = e as ApiError;
    return NextResponse.json(
      { detail: err.detail ?? "Đăng tin thất bại" },
      { status: err.status ?? 500 },
    );
  }
}
