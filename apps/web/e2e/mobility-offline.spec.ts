import { expect, test as base } from "@playwright/test";
import type { NearbyRequest, RouteRequest } from "../src/lib/mobility-contracts";
import {
  installMobilityTransport,
  syntheticNearbyResult,
  syntheticRouteResult,
  type MobilityTransport,
} from "./mobility-fixtures";

const test = base.extend<{ mobility: MobilityTransport }>({
  mobility: async ({ page }, use) => {
    const transport = await installMobilityTransport(page);
    await use(transport);
    expect(
      transport.externalAttempts,
      `Browser attempted external requests: ${transport.externalAttempts.join(", ")}`,
    ).toEqual([]);
  },
});

async function openMap(page: import("@playwright/test").Page) {
  await page.goto("/map");
  await expect(page.getByRole("heading", { name: "Bản đồ di chuyển", level: 1 })).toBeVisible();
  await expect(page.getByTestId("mobility-map")).toBeVisible();
  await expect(page.getByTestId("mobility-map").locator('[data-campus-id="khu_i"]')).toBeVisible();
  await expect(page.locator('[data-listing-id="900001"]')).toBeVisible();
}

async function selectListing(
  page: import("@playwright/test").Page,
  id: number,
) {
  await page.locator(`[data-listing-id="${id}"]`).click();
  await expect(page.locator(`[data-listing-id="${id}"]`)).toHaveAttribute(
    "aria-pressed",
    "true",
  );
}

test("pages the full 789 catalog and keeps unknown fields and missing coordinates explicit", async ({
  page,
  mobility,
}, testInfo) => {
  mobility.setCatalogTotal(789);
  await openMap(page);

  await expect(page.getByTestId("catalog-count")).toHaveText("789 tin");
  await expect(page.locator("[data-listing-id]")).toHaveCount(789);
  const ids = await page.locator("[data-listing-id]").evaluateAll((rows) =>
    rows.map((row) => row.getAttribute("data-listing-id")),
  );
  expect(new Set(ids).size).toBe(789);
  expect(ids.at(-2)).toBe("900788");
  expect(ids.at(-1)).toBe("900789");
  expect(await page.locator('[data-listing-pin-id="900788"]').count()).toBe(0);
  expect(await page.locator('[data-listing-pin-id="900789"]').count()).toBe(0);

  const pages = mobility.requests
    .filter((entry) => entry.method === "GET" && entry.path === "/api/mobility/listings")
    .map((entry) => Number(entry.query.page))
    .sort((a, b) => a - b);
  expect([...new Set(pages)]).toEqual([1, 2, 3, 4, 5, 6, 7, 8]);
  expect(pages.filter((pageNumber) => pageNumber === 1).length).toBeGreaterThanOrEqual(1);
  expect(pages.filter((pageNumber) => pageNumber === 1).length).toBeLessThanOrEqual(2);
  for (const pageNumber of [2, 3, 4, 5, 6, 7, 8]) {
    expect(pages.filter((page) => page === pageNumber)).toHaveLength(1);
  }
  expect(
    mobility.requests
      .filter((entry) => entry.path === "/api/mobility/listings")
      .every((entry) => entry.query.size === "100"),
  ).toBe(true);

  await selectListing(page, 900001);
  await expect(page.getByText("Diện tích chưa rõ", { exact: true })).toBeVisible();
  await expect(page.getByText("Loại chỗ ở chưa xác định", { exact: true })).toBeVisible();
  await expect(page.getByText("Mô tả chưa đầy đủ", { exact: true })).toBeVisible();
  await expect(page.getByText("Điều kiện thuê hoặc sang nhượng chưa xác minh", { exact: true })).toBeVisible();
  await expect(page.getByText("Có thể kết hợp ở với mục đích khác", { exact: true })).toBeVisible();
  await expect(page.getByText(/<script>window\.__fixtureInjected=true<\/script>/)).toBeVisible();
  await expect(
    page.locator("script:not([src])").filter({ hasText: "__fixtureInjected" }),
  ).toHaveCount(0);
  await expect(page.getByRole("link", { name: "Liên hệ nguồn tin" })).toHaveCount(0);

  await expect(page.getByTestId("map-tile-status")).toHaveAttribute("data-status", "disabled");
  await expect(page.getByTestId("map-tile-status")).toContainText("Chưa cấu hình bản đồ nền");
  await expect(page.locator('script[src*="maps.googleapis.com"]')).toHaveCount(0);
  await expect(page.locator('script[src*="maps.google.com"]')).toHaveCount(0);
  await expect(page.getByTestId("mobility-map").locator('[data-campus-id="khu_i"]')).toHaveAttribute("data-lat", "10.11");
  await expect(page.getByTestId("mobility-map").locator('[data-campus-id="khu_iii"]')).toHaveAttribute("data-lat", "10.33");

  await page.screenshot({ path: testInfo.outputPath("mobility-offline-ui.png") });

  await selectListing(page, 900002);
  const contact = page.getByRole("link", { name: "Liên hệ nguồn tin" });
  await expect(contact).toHaveAttribute("href", "https://contact.example.test/listing/2");
  await expect(contact).toHaveAttribute("target", "_blank");
  await expect(contact).toHaveAttribute("rel", /noopener/);
});

test("renders all four modes, keeps keyless statuses null, and sends an offset-aware bus departure", async ({
  page,
  mobility,
}) => {
  mobility.setRouteResponder((request: RouteRequest) => {
    if (request.requested_mode === "MOTORBIKE") {
      return {
        status: 200,
        body: syntheticRouteResult(request, { warning: true }),
      };
    }
    const status = request.requested_mode === "WALK"
      ? "CAPABILITY_UNVERIFIED"
      : request.requested_mode === "BICYCLE"
        ? "UNSUPPORTED_MODE"
        : "NOT_CONFIGURED";
    return {
      status: 200,
      body: syntheticRouteResult(request, { status }),
    };
  });
  await openMap(page);
  await selectListing(page, 900001);

  const mode = page.getByLabel("Phương tiện");
  await expect(mode.locator("option")).toHaveCount(4);
  await expect(mode.locator('option[value="MOTORBIKE"]')).toContainText("chưa được hỗ trợ");
  await expect(mode.locator('option[value="BUS"]')).toContainText("chưa được hỗ trợ");
  await mode.selectOption("MOTORBIKE");
  await page.getByRole("button", { name: "Tính tuyến tới khu đã chọn" }).click();
  const motorbikeResult = page.getByTestId("route-result-khu_i");
  await expect(motorbikeResult).toHaveAttribute("data-status", "OK");
  await expect(
    motorbikeResult.locator('[data-evidence-kind="SYNTHETIC_FIXTURE"]'),
  ).toContainText("Dữ liệu tổng hợp dùng cho thử nghiệm");
  await expect(motorbikeResult).toContainText(/giai đoạn beta/i);
  await expect(motorbikeResult).toContainText("1 phút");

  await mode.selectOption("WALK");
  await page.getByRole("button", { name: "Tính tuyến tới khu đã chọn" }).click();
  await expect(page.getByTestId("route-result-khu_i")).toHaveAttribute(
    "data-status",
    "CAPABILITY_UNVERIFIED",
  );
  await expect(page.getByTestId("route-result-khu_i")).not.toContainText("0 phút");

  await mode.selectOption("BICYCLE");
  await page.getByRole("button", { name: "Tính tuyến tới khu đã chọn" }).click();
  await expect(page.getByTestId("route-result-khu_i")).toHaveAttribute(
    "data-status",
    "UNSUPPORTED_MODE",
  );

  await mode.selectOption("BUS");
  const departure = page.getByLabel("Giờ khởi hành xe buýt");
  await expect(departure).toBeVisible();
  await departure.fill("2030-04-05T09:30");
  await page.getByRole("button", { name: "Tính tuyến tới khu đã chọn" }).click();
  await expect(page.getByTestId("route-result-khu_i")).toHaveAttribute(
    "data-status",
    "NOT_CONFIGURED",
  );
  const busRequest = mobility.requests
    .filter((entry) => entry.path === "/api/mobility/routes")
    .map((entry) => entry.body as RouteRequest)
    .find((entry) => entry.requested_mode === "BUS");
  expect(busRequest?.departure_time).toBe("2030-04-05T09:30:00+07:00");
  expect(busRequest?.direction).toBe("LISTING_TO_CAMPUS");
});

test("keeps the three campus route responses and errors independent", async ({ page, mobility }) => {
  mobility.setRouteResponder((request: RouteRequest) => ({
    status: 200,
    body: syntheticRouteResult(request, {
      status: request.campus_id === "khu_ii" ? "PROVIDER_ERROR" : "OK",
    }),
  }));
  await openMap(page);
  await selectListing(page, 900001);
  await page.getByRole("button", { name: "Tính tới cả 3 khu" }).click();

  for (const id of ["khu_i", "khu_ii", "khu_iii"] as const) {
    await expect(page.getByTestId(`route-result-${id}`)).toBeVisible();
  }
  await expect(page.getByTestId("route-result-khu_i")).toHaveAttribute("data-status", "OK");
  await expect(page.getByTestId("route-result-khu_ii")).toHaveAttribute(
    "data-status",
    "PROVIDER_ERROR",
  );
  await expect(page.getByTestId("route-result-khu_iii")).toHaveAttribute("data-status", "OK");

  const campusRequests = mobility.requests
    .filter((entry) => entry.path === "/api/mobility/routes")
    .map((entry) => (entry.body as RouteRequest).campus_id)
    .sort();
  expect(campusRequests).toEqual(["khu_i", "khu_ii", "khu_iii"]);
});

test("submits nearby radius and categories and labels straight-line distance and fixture provenance", async ({
  page,
  mobility,
}) => {
  mobility.setNearbyResponder((request: NearbyRequest) => ({
    status: 200,
    body: syntheticNearbyResult(request),
  }));
  await openMap(page);
  await selectListing(page, 900001);
  await page.getByLabel("Bán kính tiện ích").selectOption("2000");
  await page.getByLabel("Danh mục tiện ích").selectOption(["grocery", "pharmacy"]);
  await page.getByRole("button", { name: "Tìm tiện ích quanh tin" }).click();

  const result = page.getByTestId("nearby-result");
  await expect(result).toHaveAttribute("data-status", "OK");
  await expect(
    result.locator('[data-evidence-kind="SYNTHETIC_FIXTURE"]'),
  ).toContainText("Dữ liệu tổng hợp dùng cho thử nghiệm");
  await expect(result).toContainText("Bán kính 2.000 m");
  await expect(result).toContainText("khoảng cách đường thẳng");
  await expect(result).toContainText("175 m");
  await expect(result).toContainText("Độ phủ một phần");

  const nearbyRequest = mobility.requests
    .filter((entry) => entry.path === "/api/mobility/nearby")
    .map((entry) => entry.body as NearbyRequest)[0];
  expect(nearbyRequest).toEqual({
    listing_id: 900001,
    radius_m: 2000,
    categories: ["grocery", "pharmacy"],
  });

  mobility.setNearbyResponder((request) => ({
    status: 200,
    body: syntheticNearbyResult(request, { status: "EMPTY" }),
  }));
  await page.getByRole("button", { name: "Tìm tiện ích quanh tin" }).click();
  await expect(page.getByTestId("nearby-result")).toHaveAttribute("data-status", "EMPTY");
  await expect(page.getByTestId("nearby-result")).toContainText("Không ghi nhận tiện ích nào");

  mobility.setNearbyResponder((request) => ({
    status: 200,
    body: syntheticNearbyResult(request, { status: "CAPABILITY_UNVERIFIED" }),
  }));
  await page.getByRole("button", { name: "Tìm tiện ích quanh tin" }).click();
  await expect(page.getByTestId("nearby-result")).toHaveAttribute(
    "data-status",
    "CAPABILITY_UNVERIFIED",
  );
  await expect(page.getByTestId("nearby-result")).toContainText("chưa được xác minh");
});

test("keeps live Google route geometry and places off the Leaflet map", async ({
  page,
  mobility,
}) => {
  mobility.setRouteResponder((request) => ({
    status: 200,
    body: {
      ...syntheticRouteResult(request),
      evidence_kind: "LIVE",
      warnings: [],
    },
  }));
  mobility.setNearbyResponder((request) => ({
    status: 200,
    body: {
      ...syntheticNearbyResult(request),
      evidence_kind: "LIVE",
      items: [
        {
          provider_place_id: "live-place-must-not-be-mapped",
          name: "Nội dung Google trực tiếp fixture",
          category: "grocery",
          lat: 10.12,
          lng: 105.12,
          straight_line_distance_m: 88,
          attribution: ["Google"],
        },
      ],
    },
  }));
  await openMap(page);
  await selectListing(page, 900001);

  await page.getByRole("button", { name: "Tính tuyến tới khu đã chọn" }).click();
  await expect(page.getByTestId("route-result-khu_i")).toHaveAttribute("data-status", "OK");
  await expect(page.getByTestId("map-google-rejected")).toBeVisible();
  const map = page.getByTestId("mobility-map");
  await expect(map.locator('[data-route-source="LIVE"]')).toHaveCount(0);

  await page.getByRole("button", { name: "Tìm tiện ích quanh tin" }).click();
  await expect(page.getByText("Nội dung Google trực tiếp fixture")).toBeVisible();
  await expect(map.locator('[data-nearby-place-id="live-place-must-not-be-mapped"]')).toHaveCount(0);
});

test("ignores a late failed route after selection, campus, mode, and departure identity change", async ({
  page,
  mobility,
}) => {
  mobility.setRouteResponder((request) => ({
    status: 200,
    body: syntheticRouteResult(request),
  }));
  await openMap(page);
  await selectListing(page, 900001);
  await page.getByLabel("Khuôn viên", { exact: true }).selectOption("khu_i");
  await page.getByLabel("Phương tiện").selectOption("MOTORBIKE");

  const stale = mobility.holdNextRoute(
    (request) => request.listing_id === 900001 && request.campus_id === "khu_i",
  );
  await page.getByRole("button", { name: "Tính tuyến tới khu đã chọn" }).click();
  const staleRequest = await stale.seen;
  expect(staleRequest.requested_mode).toBe("MOTORBIKE");

  await selectListing(page, 900002);
  await page.getByLabel("Khuôn viên", { exact: true }).selectOption("khu_ii");
  await page.getByLabel("Phương tiện").selectOption("BUS");
  await page.getByLabel("Giờ khởi hành xe buýt").fill("2030-04-05T10:45");
  await page.getByRole("button", { name: "Tính tuyến tới khu đã chọn" }).click();
  const current = page.getByTestId("route-result-khu_ii");
  await expect(current).toHaveAttribute("data-status", "OK");
  await expect(current).toContainText("2 phút");
  const currentRequest = mobility.requests
    .filter((entry) => entry.path === "/api/mobility/routes")
    .map((entry) => entry.body as RouteRequest)
    .find((entry) => entry.listing_id === 900002);
  expect(currentRequest).toMatchObject({
    listing_id: 900002,
    campus_id: "khu_ii",
    requested_mode: "BUS",
    departure_time: "2030-04-05T10:45:00+07:00",
  });

  stale.release({
    status: 503,
    body: { detail: "provider api key=synthetic-secret" },
  });
  await stale.settled;
  await expect(current).toHaveAttribute("data-status", "OK");
  await expect(current).toContainText("2 phút");
  await expect(page.getByTestId("route-result-khu_i")).toHaveCount(0);
  await expect(page.getByText(/synthetic-secret/)).toHaveCount(0);
});

test("ignores a late failed nearby response after listing, radius, and categories change", async ({
  page,
  mobility,
}) => {
  mobility.setNearbyResponder((request) => ({
    status: 200,
    body: syntheticNearbyResult(request),
  }));
  await openMap(page);
  await selectListing(page, 900001);
  await page.getByLabel("Bán kính tiện ích").selectOption("500");
  await page.getByLabel("Danh mục tiện ích").selectOption(["grocery"]);

  const stale = mobility.holdNextNearby(
    (request) => request.listing_id === 900001 && request.radius_m === 500,
  );
  await page.getByRole("button", { name: "Tìm tiện ích quanh tin" }).click();
  await stale.seen;

  await selectListing(page, 900002);
  await page.getByLabel("Bán kính tiện ích").selectOption("2000");
  await page.getByLabel("Danh mục tiện ích").selectOption(["pharmacy", "market"]);
  await page.getByRole("button", { name: "Tìm tiện ích quanh tin" }).click();
  const current = page.getByTestId("nearby-result");
  await expect(current).toHaveAttribute("data-status", "OK");
  await expect(current).toContainText("Bán kính 2.000 m");

  const currentRequest = mobility.requests
    .filter((entry) => entry.path === "/api/mobility/nearby")
    .map((entry) => entry.body as NearbyRequest)
    .find((entry) => entry.listing_id === 900002);
  expect(currentRequest).toEqual({
    listing_id: 900002,
    radius_m: 2000,
    categories: ["market", "pharmacy"],
  });

  stale.release({
    status: 503,
    body: { detail: "provider api key=synthetic-secret" },
  });
  await stale.settled;
  await expect(current).toHaveAttribute("data-status", "OK");
  await expect(current).toContainText("Tiện ích tổng hợp fixture");
  await expect(page.getByText(/synthetic-secret/)).toHaveCount(0);
});

test("same-origin mobility proxy returns a generic no-store error when its configured loopback is unavailable", async ({
  request,
}) => {
  const rejectedHost = await request.get(
    "/api/mobility/listings?page=2&size=100&host=https%3A%2F%2Fattacker.example",
  );
  expect(rejectedHost.status()).toBe(400);
  expect(rejectedHost.headers()["cache-control"]).toContain("no-store");
  const rejectedBody = await rejectedHost.text();
  expect(rejectedBody).toContain("Yêu cầu không hợp lệ");
  expect(rejectedBody).not.toContain("attacker.example");

  const response = await request.get("/api/mobility/listings?page=2&size=100");
  expect(response.status()).toBe(502);
  expect(response.headers()["cache-control"]).toContain("no-store");
  const body = await response.text();
  expect(body).toContain("Dịch vụ di chuyển tạm thời không khả dụng");
  expect(body).not.toContain("127.0.0.1");
  expect(body).not.toContain("attacker.example");
  expect(body).not.toContain("provider");
});
