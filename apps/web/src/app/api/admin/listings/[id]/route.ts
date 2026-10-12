import { NextResponse } from "next/server";
import {
  updateAdminListingStatus,
  type AdminListingStatus,
  type ApiError,
} from "@/lib/api";
import { withAccessToken } from "@/lib/authenticated-api";

export async function PATCH(req: Request, { params }: { params: { id: string } }) {
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
    return NextResponse.json(
      await withAccessToken((token) =>
        updateAdminListingStatus(token, params.id, body.status as AdminListingStatus),
      ),
    );
  } catch (error) {
    const err = error as ApiError;
    return NextResponse.json(
      { detail: err.detail ?? "Cập nhật bài tin thất bại" },
      { status: err.status ?? 500 },
    );
  }
}
