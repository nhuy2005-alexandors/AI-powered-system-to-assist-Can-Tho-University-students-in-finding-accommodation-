import { NextResponse } from "next/server";
import {
  updateAdminListingStatus,
  type AdminListingStatus,
  type ApiError,
} from "@/lib/api";
import { getAccessToken } from "@/lib/session";

export async function PATCH(req: Request, { params }: { params: { id: string } }) {
  const token = getAccessToken();
  if (!token) {
    return NextResponse.json({ detail: "Chưa đăng nhập" }, { status: 401 });
  }
  let body: { status?: AdminListingStatus };
  try {
    body = await req.json();
  } catch {
    return NextResponse.json({ detail: "Body không hợp lệ" }, { status: 400 });
  }
  if (!body.status) {
    return NextResponse.json({ detail: "Thiếu trạng thái bài tin" }, { status: 400 });
  }
  try {
    return NextResponse.json(await updateAdminListingStatus(token, params.id, body.status));
  } catch (error) {
    const err = error as ApiError;
    return NextResponse.json(
      { detail: err.detail ?? "Cập nhật bài tin thất bại" },
      { status: err.status ?? 500 },
    );
  }
}
