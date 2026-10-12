import type {
  Campus,
  CatalogListing,
  CatalogPage,
  NearbyRequest,
  NearbyResult,
  RouteRequest,
  RouteResult,
} from "@/lib/mobility-contracts";

const PAGE_SIZE = 100;

export class MobilityApiError extends Error {}

async function readJson<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(path, {
      ...init,
      cache: "no-store",
      headers: init?.body
        ? { "Content-Type": "application/json", ...init.headers }
        : init?.headers,
    });
  } catch {
    throw new MobilityApiError("Không thể kết nối dịch vụ di chuyển.");
  }
  if (!response.ok) {
    if (response.status === 404) throw new MobilityApiError("Không tìm thấy tin đăng.");
    if (response.status === 422 || response.status === 400) {
      throw new MobilityApiError("Thông tin yêu cầu chưa hợp lệ.");
    }
    if (response.status === 429) {
      throw new MobilityApiError("Dịch vụ đang giới hạn yêu cầu, hãy thử lại sau.");
    }
    throw new MobilityApiError("Dịch vụ di chuyển hiện chưa thể trả lời.");
  }
  try {
    return (await response.json()) as T;
  } catch {
    throw new MobilityApiError("Dịch vụ di chuyển trả về dữ liệu không hợp lệ.");
  }
}

export async function getMobilityCampuses(signal?: AbortSignal): Promise<Campus[]> {
  return readJson<Campus[]>("/api/mobility/campuses", { signal });
}

export async function getMobilityCatalog(signal?: AbortSignal): Promise<CatalogListing[]> {
  const first = await readJson<CatalogPage>(
    `/api/mobility/listings?page=1&size=${PAGE_SIZE}`,
    { signal },
  );
  if (!Number.isSafeInteger(first.total) || first.total < 0 || first.page !== 1) {
    throw new MobilityApiError("Không thể xác nhận các trang dữ liệu tin đăng.");
  }
  const pageCount = Math.ceil(first.total / PAGE_SIZE);
  const laterPages = await Promise.all(
    Array.from({ length: Math.max(0, pageCount - 1) }, (_, offset) => {
      const page = offset + 2;
      return readJson<CatalogPage>(
        `/api/mobility/listings?page=${page}&size=${PAGE_SIZE}`,
        { signal },
      );
    }),
  );
  const pages = [first, ...laterPages];
  if (
    pages.some(
      (page, index) =>
        page.total !== first.total || page.page !== index + 1 || page.size !== PAGE_SIZE,
    )
  ) {
    throw new MobilityApiError("Các trang tin đăng không khớp cùng một danh mục.");
  }
  const items = pages.flatMap((page) => page.items);
  const ids = new Set(items.map((listing) => listing.id));
  if (items.length !== first.total || ids.size !== items.length) {
    throw new MobilityApiError("Danh mục tin đăng bị thiếu hoặc trùng dữ liệu.");
  }
  return items;
}

export async function postMobilityRoute(
  body: RouteRequest,
  signal: AbortSignal,
): Promise<RouteResult> {
  return readJson<RouteResult>("/api/mobility/routes", {
    method: "POST",
    body: JSON.stringify(body),
    signal,
  });
}

export async function postMobilityNearby(
  body: NearbyRequest,
  signal: AbortSignal,
): Promise<NearbyResult> {
  return readJson<NearbyResult>("/api/mobility/nearby", {
    method: "POST",
    body: JSON.stringify(body),
    signal,
  });
}
