import { NextResponse } from "next/server";
import { deleteListing, updateListing, type ApiError, type ListingInput } from "@/lib/api";
import { getAccessToken } from "@/lib/session";

export async function PUT(req: Request, { params }: { params: { id: string } }) {
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

  try {
    const listing = await updateListing(token, params.id, body);
    return NextResponse.json(listing);
  } catch (e) {
    const err = e as ApiError;
    return NextResponse.json(
      { detail: err.detail ?? "Sửa tin thất bại" },
      { status: err.status ?? 500 },
    );
  }
}

export async function DELETE(_req: Request, { params }: { params: { id: string } }) {
  const token = getAccessToken();
  if (!token) {
    return NextResponse.json({ detail: "Chưa đăng nhập" }, { status: 401 });
  }

  try {
    await deleteListing(token, params.id);
    return new NextResponse(null, { status: 204 });
  } catch (e) {
    const err = e as ApiError;
    return NextResponse.json(
      { detail: err.detail ?? "Xóa tin thất bại" },
      { status: err.status ?? 500 },
    );
  }
}
