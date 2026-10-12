import { NextResponse } from "next/server";
import {
  createReview,
  getListingReviews,
  type ApiError,
} from "@/lib/api";
import { withAccessToken } from "@/lib/authenticated-api";


export async function GET(
  req: Request,
  { params }: { params: { id: string } },
) {
  const url = new URL(req.url);
  const page = Number(url.searchParams.get("page") || 1);
  const size = Number(url.searchParams.get("size") || 20);
  try {
    return NextResponse.json(await getListingReviews(params.id, page, size));
  } catch (error) {
    const apiError = error as ApiError;
    return NextResponse.json(
      { detail: apiError.detail || "Không tải được đánh giá" },
      { status: apiError.status || 502 },
    );
  }
}


export async function POST(
  req: Request,
  { params }: { params: { id: string } },
) {
  let body: { rating?: number; comment?: string };
  try {
    body = await req.json();
  } catch {
    return NextResponse.json({ detail: "Body không hợp lệ" }, { status: 400 });
  }

  if (!body || !Number.isInteger(body.rating) || typeof body.comment !== "string" || !body.comment.trim()) {
    return NextResponse.json(
      { detail: "Vui lòng chọn số sao và nhập bình luận" },
      { status: 400 },
    );
  }

  try {
    const review = await withAccessToken((token) =>
      createReview(token, params.id, {
        rating: body.rating as number,
        comment: body.comment!.trim(),
      }),
    );
    return NextResponse.json(review, { status: 201 });
  } catch (error) {
    const apiError = error as ApiError;
    return NextResponse.json(
      { detail: apiError.detail || "Không gửi được đánh giá" },
      { status: apiError.status || 502 },
    );
  }
}
