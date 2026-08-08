import { NextResponse } from "next/server";
import { getListingRoute, type ApiError } from "@/lib/api";

// Proxy same-origin cho polyline campus→tin. Browser KHÔNG gọi thẳng FastAPI được:
// API chưa bật CORS nên fetch localhost:3000 → localhost:8000 bị preflight chặn
// ("No 'Access-Control-Allow-Origin'"), lỗi bị catch nuốt → map không vẽ đường.
// Route Handler chạy server-side nên dùng API_INTERNAL_URL (api:8000 trong docker).
export async function GET(req: Request, { params }: { params: { id: string } }) {
  const campus = Number(new URL(req.url).searchParams.get("campus") ?? 1);
  if (!Number.isInteger(campus) || campus < 0 || campus > 2) {
    return NextResponse.json({ detail: "campus phải là 0, 1 hoặc 2" }, { status: 400 });
  }

  try {
    const path = await getListingRoute(params.id, campus);
    return NextResponse.json(path);
  } catch (e) {
    const err = e as ApiError;
    return NextResponse.json(
      { detail: err.detail ?? "Không lấy được đường đi" },
      { status: err.status ?? 500 },
    );
  }
}
