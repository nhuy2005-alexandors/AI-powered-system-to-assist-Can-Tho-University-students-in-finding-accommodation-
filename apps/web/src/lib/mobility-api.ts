import { API_URL } from "@/lib/config";

const NO_STORE_HEADERS = {
  "Cache-Control": "no-store, max-age=0",
  Pragma: "no-cache",
};

type JsonObject = Record<string, unknown>;

function errorMessage(status: number): string {
  if (status === 400 || status === 422) return "Yêu cầu không hợp lệ.";
  if (status === 404) return "Không tìm thấy dữ liệu theo yêu cầu.";
  if (status === 429) return "Dịch vụ đang giới hạn yêu cầu.";
  return "Dịch vụ di chuyển tạm thời không khả dụng.";
}

export function mobilityDisabled(): Response {
  return Response.json(
    { error: "Dịch vụ di chuyển chưa được bật." },
    { status: 404, headers: NO_STORE_HEADERS },
  );
}

export function invalidMobilityRequest(): Response {
  return Response.json(
    { error: "Yêu cầu không hợp lệ." },
    { status: 400, headers: NO_STORE_HEADERS },
  );
}

export async function readAllowedMobilityJson(
  request: Request,
  allowedFields: readonly string[],
): Promise<JsonObject | null> {
  let body: unknown;
  try {
    body = await request.json();
  } catch {
    return null;
  }
  if (body === null || typeof body !== "object" || Array.isArray(body)) return null;
  const fields = body as JsonObject;
  if (Object.keys(fields).some((key) => !allowedFields.includes(key))) return null;
  return fields;
}

export async function proxyMobilityJson(
  path: string,
  init: { method: "GET" | "POST"; body?: JsonObject },
): Promise<Response> {
  if (process.env.MOBILITY_ENABLED !== "true") return mobilityDisabled();

  try {
    const response = await fetch(`${API_URL.replace(/\/+$/, "")}${path}`, {
      method: init.method,
      headers: init.body ? { Accept: "application/json", "Content-Type": "application/json" } : { Accept: "application/json" },
      body: init.body ? JSON.stringify(init.body) : undefined,
      cache: "no-store",
      redirect: "error",
    });

    if (!response.ok) {
      return Response.json(
        { error: errorMessage(response.status) },
        { status: response.status, headers: NO_STORE_HEADERS },
      );
    }

    try {
      const payload: unknown = await response.json();
      return Response.json(payload, {
        status: response.status,
        headers: NO_STORE_HEADERS,
      });
    } catch {
      return Response.json(
        { error: "Dịch vụ di chuyển trả về dữ liệu không hợp lệ." },
        { status: 502, headers: NO_STORE_HEADERS },
      );
    }
  } catch {
    return Response.json(
      { error: "Dịch vụ di chuyển tạm thời không khả dụng." },
      { status: 502, headers: NO_STORE_HEADERS },
    );
  }
}
