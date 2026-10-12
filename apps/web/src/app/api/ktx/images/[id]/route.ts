import { NextResponse } from "next/server";
import { API_URL } from "@/lib/config";

export async function GET(_: Request, { params }: { params: { id: string } }) {
  if (!/^[a-f0-9-]{36}$/.test(params.id)) return new NextResponse(null, { status: 404 });
  try {
    const response = await fetch(`${API_URL}/ktx/images/${params.id}`, { cache: "no-store" });
    if (!response.ok) return new NextResponse(null, { status: response.status });
    return new NextResponse(response.body, { headers: {
      "Content-Type": "image/jpeg", "Cache-Control": "public, max-age=86400", "X-Content-Type-Options": "nosniff",
    } });
  } catch { return new NextResponse(null, { status: 502 }); }
}
