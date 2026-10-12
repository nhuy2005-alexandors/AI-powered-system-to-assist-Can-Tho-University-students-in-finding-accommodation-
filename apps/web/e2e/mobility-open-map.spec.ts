import { expect, test as base } from "@playwright/test";
import {
  installMobilityTransport,
  syntheticCampuses,
  syntheticCatalogPage,
  syntheticNearbyResult,
  syntheticRouteResult,
  type MobilityTransport,
} from "./mobility-fixtures";
import type { NearbyRequest, RouteRequest } from "../src/lib/mobility-contracts";
import type { ListingLayerSnapshot } from "../src/components/mobility/leaflet-map-provider";

async function expectListingMembers(page: import("@playwright/test").Page, total: number) {
  const expected = syntheticCatalogPage(1, total, total).items.flatMap((listing) =>
    listing.position ? [{ id: listing.id, lat: listing.position.lat, lng: listing.position.lng }] : [],
  );
  await expect.poll(() => page.getByTestId("mobility-map").evaluate((container) => {
    let snapshot: ListingLayerSnapshot | null = null;
    container.dispatchEvent(new CustomEvent("mobility:listing-layer-snapshot", {
      detail: { respond: (value: ListingLayerSnapshot) => { snapshot = value; } },
    }));
    return snapshot;
  })).toMatchObject({ state: "READY", members: expected });
}

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
  await expect(page.getByTestId("catalog-count")).not.toHaveText("Đang tải danh mục…");
}

async function selectListing(
  page: import("@playwright/test").Page,
  id: number,
) {
  const row = page.locator(`[data-listing-id="${id}"]`);
  await row.click();
  await expect(row).toHaveAttribute("aria-pressed", "true");
}

test("renders all 789 catalog cards and 787 positioned listings on Leaflet", async ({
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
  expect(ids.slice(-2)).toEqual(["900788", "900789"]);

  const map = page.getByTestId("mobility-map");
  await expect(map).toBeVisible();
  await expect(map).toHaveClass(/leaflet-container/);
  await expectListingMembers(page, 789);
  await expect(map.locator('[data-listing-pin-id="900788"]')).toHaveCount(0);
  await expect(map.locator('[data-listing-pin-id="900789"]')).toHaveCount(0);
  await expect(map.locator("[data-campus-id]")).toHaveCount(3);
  await expect(map.locator('[data-campus-id="khu_i"]')).toHaveAttribute(
    "data-verification",
    "PROVISIONAL",
  );
  await expect(page.getByTestId("map-tile-status")).toHaveAttribute("data-status", "disabled");
  await expect(map.locator(".leaflet-tile")).toHaveCount(0);
  expect(mobility.requests.some((entry) => entry.path.includes("/listings/nearby"))).toBe(false);

  await selectListing(page, 900001);
  await expect(page.getByText("Diện tích chưa rõ", { exact: true })).toBeVisible();
  await expect(page.getByText("Mô tả chưa đầy đủ", { exact: true })).toBeVisible();
  await expect(page.getByRole("region", { name: "Chi tiết tin được chọn" }).getByRole("link", { name: "Xem tin gốc" })).toHaveAttribute(
    "href",
    "https://source.example.test/listing/1",
  );
  await expect(page.getByRole("link", { name: "Liên hệ nguồn tin" })).toHaveCount(0);
  const screenshotPath = testInfo.outputPath("mobility-open-map.png");
  await page.screenshot({ path: screenshotPath });
  await testInfo.attach("mobility-open-map", {
    path: screenshotPath,
    contentType: "image/png",
  });
});

test("uses the fetched campus DTO and preserves listing and POI layers", async ({
  page,
  mobility,
}) => {
  mobility.setCatalogTotal(789);
  const campuses = syntheticCampuses();
  campuses[0] = {
    ...campuses[0],
    name: "Sentinel campus from transport",
    lat: 10.1777,
    lng: 105.1777,
  };
  await page.route("http://localhost:3031/api/mobility/campuses", (route) =>
    route.fulfill({ status: 200, json: campuses }),
  );
  mobility.setNearbyResponder((request: NearbyRequest) => ({
    status: 200,
    body: {
      ...syntheticNearbyResult(request),
      provider: "osm_overpass",
      evidence_kind: "SYNTHETIC_FIXTURE",
    },
  }));

  await openMap(page);
  await expect(page.getByTestId("catalog-count")).toHaveText("789 tin");
  const map = page.getByTestId("mobility-map");
  await expect(map).toHaveClass(/leaflet-container/);
  await expectListingMembers(page, 789);
  const sentinel = map.locator('[data-campus-id="khu_i"]');
  await expect(sentinel).toHaveAttribute("data-lat", "10.1777");
  await expect(sentinel).toHaveAttribute("data-lng", "105.1777");
  await expect(
    map.locator(".leaflet-tooltip").filter({ hasText: "Sentinel campus from transport" }),
  ).toBeVisible();

  await selectListing(page, 900001);
  await page.getByRole("button", { name: "Tìm tiện ích quanh tin" }).click();
  await expect(map.locator("[data-nearby-place-id]")).toHaveCount(1);
  await expectListingMembers(page, 789);
  await expect(map.locator("[data-campus-id]")).toHaveCount(3);
  await expect(map.locator('[data-nearby-place-id="khu_i"]')).toHaveCount(0);
});

test("unmounts and remounts Leaflet cleanly after navigating away", async ({ page, mobility }) => {
  const pageErrors: string[] = [];
  page.on("pageerror", (error) => pageErrors.push(error.message));
  await openMap(page);
  expect(mobility.requests.some((entry) => entry.path === "/api/mobility/campuses")).toBe(true);
  expect(mobility.requests.some((entry) => entry.path === "/api/mobility/listings")).toBe(true);
  await expectListingMembers(page, 3);

  await page.getByRole("link", { name: "Trọ CTU, trang chủ" }).click();
  await expect(page.getByRole("heading", { name: "Trọ CTU", level: 1 })).toBeVisible();
  await page.goBack();

  await expect(page.getByRole("heading", { name: "Bản đồ di chuyển", level: 1 })).toBeVisible();
  const map = page.getByTestId("mobility-map");
  await expect(map).toHaveClass(/leaflet-container/);
  await expectListingMembers(page, 3);
  expect(pageErrors).toEqual([]);
});

test("draws open-provider synthetic route and POI layers with visible fixture provenance", async ({
  page,
  mobility,
}) => {
  mobility.setRouteResponder((request: RouteRequest) => ({
    status: 200,
    body: {
      ...syntheticRouteResult(request),
      provider: "ors",
      provider_profile: "foot-walking",
      attribution: ["OpenRouteService synthetic test fixture"],
      evidence_kind: "SYNTHETIC_FIXTURE",
    },
  }));
  mobility.setNearbyResponder((request: NearbyRequest) => {
    const result = syntheticNearbyResult(request);
    return {
      status: 200,
      body: {
        ...result,
        provider: "osm_overpass",
        evidence_kind: "SYNTHETIC_FIXTURE",
        items: [
          {
            provider_place_id: "synthetic-osm-poi-must-not-map",
            name: "POI synthetic fixture",
            category: "grocery",
            lat: 10.1015,
            lng: 105.1015,
            straight_line_distance_m: 175,
            attribution: ["OpenStreetMap synthetic test fixture"],
          },
        ],
      },
    };
  });
  await openMap(page);
  await selectListing(page, 900001);
  await page.getByLabel("Phương tiện").selectOption("WALK");

  await page.getByRole("button", { name: "Tính tuyến tới khu đã chọn" }).click();
  await expect(page.getByTestId("route-result-khu_i")).toHaveAttribute("data-status", "OK");
  const map = page.getByTestId("mobility-map");
  await expect(map.locator('[data-route-source="SYNTHETIC_FIXTURE"]')).toHaveCount(1);

  await page.getByRole("button", { name: "Tìm tiện ích quanh tin" }).click();
  await expect(page.getByTestId("nearby-result")).toHaveAttribute("data-status", "OK");
  await expect(map.locator('[data-nearby-place-id="synthetic-osm-poi-must-not-map"]')).toHaveCount(1);
  await expect(page.getByTestId("map-provenance")).toContainText(
    "Dữ liệu tổng hợp dùng cho thử nghiệm",
  );
  await expect(page.getByTestId("map-attribution")).toContainText(
    "OpenRouteService synthetic test fixture",
  );
  await expect(page.getByTestId("map-attribution")).toContainText(
    "OpenStreetMap synthetic test fixture",
  );
});

test("rejects contradictory ORS route observation and provenance markers", async ({
  page,
  mobility,
}) => {
  const localTile = Buffer.from(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/S9sAAAAASUVORK5CYII=",
    "base64",
  );
  await page.route("https://127.0.0.1:3031/__p2ui_local_tile__/**", (route) =>
    route.fulfill({ status: 200, contentType: "image/png", body: localTile }),
  );
  await openMap(page);
  await selectListing(page, 900001);
  await page.getByLabel("Phương tiện").selectOption("WALK");

  const map = page.getByTestId("mobility-map");
  const routeCard = page.getByTestId("route-result-khu_i");
  const calculateRoute = page.getByRole("button", { name: "Tính tuyến tới khu đã chọn" });
  const routeReply = (
    request: RouteRequest,
    options: {
      evidenceKind: "LIVE" | "SYNTHETIC_FIXTURE";
      observedAt: string | null;
      pointSource: string | null;
      durationSeconds: number;
    },
  ) => {
    const result = syntheticRouteResult(request);
    return {
      status: 200,
      body: {
        ...result,
        provider: "ors",
        provider_profile: "foot-walking",
        attribution: ["OpenRouteService route-rendering test fixture"],
        evidence_kind: options.evidenceKind,
        observed_at: options.observedAt,
        duration_seconds: options.durationSeconds,
        polyline: result.polyline?.map((point) => ({
          ...point,
          source: options.pointSource,
        })),
      },
    };
  };

  const invalidCases = [
    { name: "missing observation time", observedAt: null, pointSource: null, durationSeconds: 777 },
    { name: "invalid observation time", observedAt: "not-a-time", pointSource: null, durationSeconds: 1377 },
    { name: "impossible calendar date", observedAt: "2026-02-30T12:00:00Z", pointSource: null, durationSeconds: 1777 },
    { name: "Google point source", observedAt: "2026-10-05T12:00:00Z", pointSource: "GoOgLe", durationSeconds: 1977 },
    { name: "Google Maps point source", observedAt: "2026-10-05T12:00:00Z", pointSource: "Google Maps", durationSeconds: 2377 },
    { name: "google_routes point source", observedAt: "2026-10-05T12:00:00Z", pointSource: "google_routes", durationSeconds: 2977 },
  ];

  let baselineDuration = 600;
  for (const invalidCase of invalidCases) {
    mobility.setRouteResponder((request) =>
      routeReply(request, {
        evidenceKind: "SYNTHETIC_FIXTURE",
        observedAt: "2026-10-05T12:00:00+07:00",
        pointSource: null,
        durationSeconds: baselineDuration,
      }),
    );
    await calculateRoute.click();
    await expect(routeCard).toContainText(`Thời gian: ${Math.round(baselineDuration / 60)} phút`);
    await expect(map.locator('[data-route-source="SYNTHETIC_FIXTURE"]')).toHaveCount(1);

    mobility.setRouteResponder((request) =>
      routeReply(request, {
        evidenceKind: "LIVE",
        observedAt: invalidCase.observedAt,
        pointSource: invalidCase.pointSource,
        durationSeconds: invalidCase.durationSeconds,
      }),
    );
    await calculateRoute.click();
    await expect(routeCard).toContainText(`Thời gian: ${Math.round(invalidCase.durationSeconds / 60)} phút`);
    await expect.soft(map.locator("[data-route-source]"), invalidCase.name).toHaveCount(0, {
      timeout: 2_000,
    });
    baselineDuration += 60;
  }
});

test("does not copy Google synthetic route or POI payloads onto the open map", async ({
  page,
  mobility,
}) => {
  mobility.setRouteResponder((request) => ({
    status: 200,
    body: {
      ...syntheticRouteResult(request),
      provider: "google",
      evidence_kind: "SYNTHETIC_FIXTURE",
    },
  }));
  mobility.setNearbyResponder((request) => ({
    status: 200,
    body: {
      ...syntheticNearbyResult(request),
      provider: "google",
      evidence_kind: "SYNTHETIC_FIXTURE",
      items: [
        {
          provider_place_id: "google-synthetic-place-must-not-map",
          name: "Google synthetic place content stays off map",
          category: "grocery",
          lat: 10.1015,
          lng: 105.1015,
          straight_line_distance_m: 175,
          attribution: ["Google synthetic fixture"],
        },
      ],
    },
  }));
  await openMap(page);
  await selectListing(page, 900001);
  await page.getByLabel("Phương tiện").selectOption("WALK");

  await page.getByRole("button", { name: "Tính tuyến tới khu đã chọn" }).click();
  await expect(page.getByTestId("route-result-khu_i")).toHaveAttribute("data-status", "OK");
  await expect(page.getByTestId("map-google-rejected")).toBeVisible();
  await page.getByRole("button", { name: "Tìm tiện ích quanh tin" }).click();

  const map = page.getByTestId("mobility-map");
  await expect(map.locator("[data-route-source]")).toHaveCount(0);
  await expect(map.locator('[data-nearby-place-id="google-synthetic-place-must-not-map"]')).toHaveCount(0);
  await expect(map).not.toContainText("Google synthetic place content stays off map");
});

if (process.env.P2UI_TEST_MAP_DISABLED === "true") {
  test("disabled mobility map shows local-only unavailable state without legacy tiles", async ({
    page,
    mobility,
  }) => {
    await page.goto("/map");
    await expect(page.getByTestId("mobility-map-unavailable")).toBeVisible();
    await expect(page.locator(".leaflet-container")).toHaveCount(0);
    await expect(page.getByTestId("offline-map")).toHaveCount(0);
    await expect(page.locator(".leaflet-tile")).toHaveCount(0);
    expect(mobility.requests).toEqual([]);
  });
}

if (process.env.P2UI_TEST_LOCAL_TILES === "true") {
  test("tile failure leaves catalog usable after mixed success and failure, then recovers on a later successful batch", async ({
    page,
    mobility,
  }) => {
    let tileAttempts = 0;
    let successfulTiles = 0;
    let failedTiles = 0;
    let recoveryAttempts = 0;
    let mode: "mixed" | "success" = "mixed";
    const png = Buffer.from(
      "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/S9sAAAAASUVORK5CYII=",
      "base64",
    );

    await page.route("https://127.0.0.1:3031/__p2ui_local_tile__/**", async (route) => {
      tileAttempts += 1;

      if (mode === "success") {
        recoveryAttempts += 1;
        successfulTiles += 1;
        await route.fulfill({ status: 200, contentType: "image/png", body: png });
        return;
      }

      if (tileAttempts % 2 === 1) {
        successfulTiles += 1;
        await route.fulfill({ status: 200, contentType: "image/png", body: png });
        return;
      }

      await page.waitForFunction(() =>
        Array.from(
          document.querySelectorAll<HTMLImageElement>("[data-testid='mobility-map'] img.leaflet-tile"),
        ).some((tile) => tile.complete && tile.naturalWidth > 0),
      );
      failedTiles += 1;
      await route.fulfill({ status: 503, contentType: "text/plain", body: "synthetic mixed tile error" });
    });

    await openMap(page);
    const map = page.getByTestId("mobility-map");
    await expect(map).toHaveAttribute("data-tile-status", "error");
    await expect(page.getByTestId("map-tile-status")).toHaveAttribute("data-status", "error");
    await expect(page.getByTestId("catalog-count")).toHaveText("3 tin");
    await selectListing(page, 900001);
    await expect(page.getByText("Diện tích chưa rõ", { exact: true })).toBeVisible();
    await expect(page.getByRole("region", { name: "Chi tiết tin được chọn" }).getByRole("link", { name: "Xem tin gốc" })).toBeVisible();
    await expect(page.getByTestId("map-attribution")).toContainText("Synthetic local tile fixture");
    expect(tileAttempts).toBeGreaterThan(1);
    expect(successfulTiles).toBeGreaterThan(0);
    expect(failedTiles).toBeGreaterThan(0);

    const recoveryBefore = recoveryAttempts;
    mode = "success";
    await map.getByRole("button", { name: "Zoom in" }).click();
    await expect.poll(() => recoveryAttempts).toBeGreaterThan(recoveryBefore);
    await expect(map).toHaveAttribute("data-tile-status", "ready");
  });

  test("tile failure leaves the catalog, source, and selected details usable", async ({
    page,
    mobility,
  }) => {
    let tileAttempts = 0;
    await page.route("https://127.0.0.1:3031/__p2ui_local_tile__/**", async (route) => {
      tileAttempts += 1;
      await route.fulfill({ status: 503, contentType: "text/plain", body: "synthetic tile error" });
    });
    await openMap(page);

    const map = page.getByTestId("mobility-map");
    await expect(page.getByTestId("map-tile-status")).toHaveAttribute("data-status", "error");
    await expect(page.getByTestId("catalog-count")).toHaveText("3 tin");
    await selectListing(page, 900001);
    await expect(page.getByText("Diện tích chưa rõ", { exact: true })).toBeVisible();
    await expect(page.getByRole("region", { name: "Chi tiết tin được chọn" }).getByRole("link", { name: "Xem tin gốc" })).toBeVisible();
    await expect(page.getByTestId("map-attribution")).toContainText(
      "Synthetic local tile fixture",
    );
    expect(tileAttempts).toBeGreaterThan(0);
    expect(mobility.requests.some((entry) => entry.path === "/api/mobility/listings")).toBe(true);
  });

  test("configured local test tile is intercepted and its attribution stays visible", async ({
    page,
    mobility,
  }) => {
    let tileAttempts = 0;
    const startupZooms = new Set<string>();
    mobility.setCatalogTotal(789);
    const png = Buffer.from(
      "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/S9sAAAAASUVORK5CYII=",
      "base64",
    );
    await page.route("https://127.0.0.1:3031/__p2ui_local_tile__/**", async (route) => {
      tileAttempts += 1;
      startupZooms.add(new URL(route.request().url()).pathname.split("/")[2]);
      await route.fulfill({ status: 200, contentType: "image/png", body: png });
    });
    await openMap(page);
    await expectListingMembers(page, 789);
    const initialMap = page.getByTestId("mobility-map");
    await expect(initialMap).toHaveAttribute("data-initial-fit-zoom", /^\d+$/);

    await expect(page.getByTestId("mobility-map")).toHaveAttribute(
      "data-tile-status",
      "ready",
    );
    await expect(page.getByTestId("map-attribution")).toContainText(
      "Synthetic local tile fixture",
    );
    expect(tileAttempts).toBeGreaterThan(0);
    expect(startupZooms.size, "only the fitted initial viewport may fetch tiles").toBe(1);
    expect([...startupZooms]).toEqual([await initialMap.getAttribute("data-initial-fit-zoom")]);
    const extents = await initialMap.evaluate((element) => ({
      south: Number(element.dataset.initialFitSouth), north: Number(element.dataset.initialFitNorth),
      west: Number(element.dataset.initialFitWest), east: Number(element.dataset.initialFitEast),
    }));
    const positions = [
      ...syntheticCatalogPage(1,789,789).items.flatMap((listing) => listing.position ? [listing.position] : []),
      ...syntheticCampuses().map((campus) => ({lat:campus.lat,lng:campus.lng})),
    ];
    expect(positions.every(p=>p.lat>=extents.south && p.lat<=extents.north &&
      p.lng>=extents.west && p.lng<=extents.east), "fitted viewport includes every fixture coordinate").toBe(true);
    expect(mobility.requests.some((entry) => entry.path === "/api/mobility/listings")).toBe(true);
  });
}
