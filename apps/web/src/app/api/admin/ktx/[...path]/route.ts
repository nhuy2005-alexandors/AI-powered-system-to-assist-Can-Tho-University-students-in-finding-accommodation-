import { NextResponse } from "next/server";
import { API_URL } from "@/lib/config";
import { withAccessToken } from "@/lib/authenticated-api";
import type { ApiError } from "@/lib/api";

export const dynamic = "force-dynamic";

async function proxy(req: Request, { params }: { params: { path: string[] } }) {
  const path = params.path.join("/");
  if (!/^(years(?:\/\d+(?:\/(?:publish|archive))?)?|images)$/.test(path)) {
    return NextResponse.json({ detail: "Đường dẫn không hợp lệ" }, { status: 404 });
  }
  const origin = req.headers.get("origin");
  if (req.method !== "GET" && origin && origin !== new URL(req.url).origin) {
    return NextResponse.json({ detail: "Yêu cầu không hợp lệ" }, { status: 403 });
  }
  const max = path === "images" ? 8 * 1024 * 1024 + 256 * 1024 : 2 * 1024 * 1024;
  if (Number(req.headers.get("content-length") || 0) > max) {
    return NextResponse.json({ detail: "Dữ liệu gửi lên quá lớn" }, { status: 413 });
  }
  try {
    let body: BodyInit | undefined;
    const multipart = req.headers.get("content-type")?.includes("multipart/form-data");
    if (req.method !== "GET") {
      const reader = req.body?.getReader();
      const chunks: Uint8Array[] = [];
      let size = 0;
      if (reader) {
        while (true) {
          const {done,value} = await reader.read();
          if (done) break;
          size += value.byteLength;
          if (size > max) { await reader.cancel(); return NextResponse.json({detail:"Dữ liệu gửi lên quá lớn"},{status:413}); }
          chunks.push(value);
        }
      }
      const bytes = new Uint8Array(size);
      let offset = 0;
      for (const chunk of chunks) { bytes.set(chunk,offset); offset += chunk.byteLength; }
      body = multipart ? await new Response(bytes,{headers:{"Content-Type":req.headers.get("content-type")!}}).formData() : new TextDecoder().decode(bytes);
    }
    if (typeof body === "string" && new TextEncoder().encode(body).length > max) {
      return NextResponse.json({ detail: "Danh mục quá lớn" }, { status: 413 });
    }
    const data = await withAccessToken(async (token) => {
      const response = await fetch(`${API_URL}/admin/ktx/${path}`, {
        method: req.method, body,
        headers: { Authorization: `Bearer ${token}`, ...(!multipart && body ? { "Content-Type": "application/json" } : {}) },
        cache: "no-store",
      });
      const data = await response.json();
      if (!response.ok) throw { status: response.status, detail: data.detail || "Không xử lý được yêu cầu KTX" };
      return data;
    });
    return NextResponse.json(data);
  } catch (error) {
    const err = error as ApiError;
    return NextResponse.json({ detail: err.detail || "Không kết nối được dịch vụ KTX" }, { status: err.status || 502 });
  }
}

export const GET = proxy;
export const POST = proxy;
export const PUT = proxy;
