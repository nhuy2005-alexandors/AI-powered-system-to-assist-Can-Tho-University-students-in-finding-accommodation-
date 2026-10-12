import { expect, test as base, type Locator, type Page } from "@playwright/test";
import { resolve } from "node:path";
import {
  installMobilityTransport,
  syntheticCatalogPage,
  syntheticListing,
  type MobilityTransport,
} from "./mobility-fixtures";

type ListingLayerSnapshot = {
  generation: number;
  state: "READY" | "UNAVAILABLE";
  members: Array<{ id: number; lat: number; lng: number }>;
};

type CatalogPageRequestObservation = {
  page: number | null;
  size: number | null;
  failureText: string | null;
};

type MapReuseTestWindow = Window & {
  next?: { router?: { push(href: string): void } };
  L?: {
    Map?: { prototype: { stop?: (...args: unknown[]) => unknown } };
    MarkerClusterGroup?: {
      prototype: { zoomToShowLayer?: (...args: unknown[]) => unknown };
    };
  };
  __mobilityMapReuseCounters?: { zoomToShowCalls: number; mapStopCalls: number };
  __restoreMobilityMapReuseHooks?: () => void;
};

type HeldChunkRequest = {
  readonly requestUrl: string;
  readonly settled: Promise<void>;
  release(): void;
};

type InitGuardMutation = {
  readonly applied: boolean;
  readonly error: string | null;
};

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
async function interceptCatalogWithDuplicateCoordinate(page: Page): Promise<{
  completedRequests: () => CatalogPageRequestObservation[];
  failedRequests: () => CatalogPageRequestObservation[];
}> {
  const completedRequests: CatalogPageRequestObservation[] = [];
  const failedRequests: CatalogPageRequestObservation[] = [];
  const observeRequest = (
    requestUrl: string,
    failureText: string | null,
  ): CatalogPageRequestObservation | null => {
    const url = new URL(requestUrl);
    if (url.pathname !== "/api/mobility/listings") return null;
    const positiveInteger = (value: string | null): number | null => {
      if (value === null || !/^\d+$/.test(value)) return null;
      const parsed = Number(value);
      return Number.isSafeInteger(parsed) && parsed > 0 ? parsed : null;
    };
    return {
      page: positiveInteger(url.searchParams.get("page")),
      size: positiveInteger(url.searchParams.get("size")),
      failureText,
    };
  };
  page.on("requestfinished", (request) => {
    const observation = observeRequest(request.url(), null);
    if (observation !== null) completedRequests.push(observation);
  });
  page.on("requestfailed", (request) => {
    const observation = observeRequest(request.url(), request.failure()?.errorText ?? null);
    if (observation !== null) failedRequests.push(observation);
  });
  await page.route("**/api/mobility/listings**", async (route) => {
    const url = new URL(route.request().url());
    const pageNumber = Number(url.searchParams.get("page") ?? "1");
    const size = Number(url.searchParams.get("size") ?? "50");
    const response = syntheticCatalogPage(pageNumber, size, 789);
    const items = response.items.map((listing) =>
      listing.id === 900_002
        ? {
            ...listing,
            position: listing.position
              ? { ...listing.position, lat: 10.1002, lng: 105.1 }
              : null,
          }
        : listing,
    );
    await route.fulfill({ status: 200, json: { ...response, items } });
  });
  return {
    completedRequests: () => [...completedRequests],
    failedRequests: () => [...failedRequests],
  };
}

async function interceptCatalogWithHostilePopupContent(page: Page): Promise<void> {
  await page.route("**/api/mobility/listings**", async (route) => {
    const url = new URL(route.request().url());
    const pageNumber = Number(url.searchParams.get("page") ?? "1");
    const size = Number(url.searchParams.get("size") ?? "50");
    const response = syntheticCatalogPage(pageNumber, size, 3);
    const items = response.items.map((listing) =>
      listing.id === 900_001
        ? {
            ...listing,
            title: '<img src="https://hostile.example.test/title.png" onerror="window.__mapPopupInjected=true">',
            address: '<svg onload="window.__mapPopupInjected=true">hostile address</svg>',
            price: null,
            source_url: "javascript:window.__mapPopupInjected=true",
          }
        : listing,
    );
    await route.fulfill({ status: 200, json: { ...response, items } });
  });
}

async function interceptCatalogForViewControls(page: Page): Promise<() => number> {
  let requestCount = 0;
  await page.route("**/api/mobility/listings**", async (route) => {
    requestCount += 1;
    const url = new URL(route.request().url());
    const pageNumber = Number(url.searchParams.get("page") ?? "1");
    const size = Number(url.searchParams.get("size") ?? "50");
    const response = syntheticCatalogPage(pageNumber, size, 789);
    const items = response.items.map((listing) => {
      if (listing.id === 900_001) {
        return { ...listing, title: "Đường 3/2 · tin theo tên" };
      }
      if (listing.id === 900_002) {
        return { ...listing, address: "Đường 3/2 · địa chỉ theo tin", price: 1_000 };
      }
      if (listing.id === 900_003) return { ...listing, price: 0 };
      if (listing.id === 900_004) {
        return {
          ...listing,
          price: 1_000,
          position: listing.position
            ? { ...listing.position, lat: 11, lng: 106 }
            : null,
        };
      }
      if (listing.id === 900_788 || listing.id === 900_789) {
        return { ...listing, price: null };
      }
      return listing;
    });

    if (pageNumber === 1) {
      const higherIdIndex = items.findIndex((listing) => listing.id === 900_004);
      const lowerIdIndex = items.findIndex((listing) => listing.id === 900_002);
      [items[higherIdIndex], items[lowerIdIndex]] = [items[lowerIdIndex], items[higherIdIndex]];
    }

    await route.fulfill({ status: 200, json: { ...response, items } });
  });
  return () => requestCount;
}

async function openMap(page: Page, total = 789): Promise<void> {
  await page.goto("/map");
  await expect(page.getByRole("heading", { name: "Bản đồ di chuyển", level: 1 })).toBeVisible();
  await expect(page.getByTestId("catalog-count")).toHaveText(`${total} tin`);
}

async function holdLocalChunk(page: Page, chunkFilename: string): Promise<HeldChunkRequest> {
  let releaseHold!: () => void;
  let settleRequest!: () => void;
  const state = { requestUrl: "", settled: false };
  const hold = new Promise<void>((resolve) => {
    releaseHold = resolve;
  });
  const settled = new Promise<void>((resolve) => {
    settleRequest = resolve;
  });
  await page.route(`**/${chunkFilename}`, async (route) => {
    state.requestUrl = route.request().url();
    try {
      await hold;
      await route.continue();
    } catch {
      // A route change may cancel a held local import.
    } finally {
      if (!state.settled) {
        state.settled = true;
        settleRequest();
      }
    }
  });
  return {
    get requestUrl() {
      return state.requestUrl;
    },
    settled,
    release: releaseHold,
  };
}

async function installInitGuardMutation(page: Page): Promise<() => InitGuardMutation> {
  const status = { applied: false, error: null as string | null };
  if (process.env.P2UI_TEST_MUTATE_INIT_GUARD !== "true") return () => status;

  await page.route("**/*MobilityMap_tsx.js", async (route) => {
    try {
      const response = await route.fetch();
      const originalBody = await response.text();
      const guard = "destroyed || initGeneration !== currentInitGeneration || !element.isConnected";
      if (!originalBody.includes(guard)) {
        status.error = "the exact served init guard was not found";
        await route.fulfill({ response, body: originalBody });
        return;
      }
      const mutatedBody = originalBody.replace(guard, "false");
      if (mutatedBody === originalBody) {
        status.error = "served init guard mutation made no change";
        await route.fulfill({ response, body: originalBody });
        return;
      }
      status.applied = true;
      await route.fulfill({ response, body: mutatedBody });
    } catch (error) {
      status.error = error instanceof Error ? error.message : String(error);
      await route.abort();
    }
  });
  return () => status;
}

async function installKeyboardNoopMutation(page: Page): Promise<void> {
  if (process.env.P2UI_TEST_MUTATE_KEYBOARD !== "true") return;
  await page.addInitScript(() => {
    document.addEventListener("keydown", (event) => {
      const target = event.target;
      if (
        event.key === "Enter" &&
        target instanceof Element &&
        target.hasAttribute("data-listing-pin-id")
      ) {
        event.preventDefault();
        event.stopImmediatePropagation();
      }
    }, true);
  });
}

async function requestListingLayerSnapshot(page: Page): Promise<ListingLayerSnapshot | null> {
  return page.getByTestId("mobility-map").evaluate((container) => {
    let snapshot: ListingLayerSnapshot | null = null;
    container.dispatchEvent(
      new CustomEvent("mobility:listing-layer-snapshot", {
        detail: {
          respond(value: ListingLayerSnapshot) {
            snapshot = value;
          },
        },
      }),
    );
    return snapshot;
  });
}

async function waitForListingLayerReady(page: Page): Promise<void> {
  await expect.poll(async () => (await requestListingLayerSnapshot(page))?.state).toBe("READY");
}

async function waitForStableMapPane(pane: Locator): Promise<void> {
  let previous: string | null = null;
  let stableReads = 0;
  await expect.poll(async () => {
    const current = await pane.getAttribute("style");
    stableReads = current === previous ? stableReads + 1 : 0;
    previous = current;
    return stableReads >= 2;
  }, { timeout: 10_000, intervals: [100, 200, 400] }).toBe(true);
}

test("cluster_keeps_every_id_including_duplicate_coordinates", async ({ page, mobility }) => {
  const pageErrors: string[] = [];
  const consoleErrors: string[] = [];
  page.on("pageerror", (error) => pageErrors.push(error.message));
  page.on("console", (message) => {
    if (message.type() === "error") consoleErrors.push(message.text());
  });
  mobility.setCatalogTotal(789);
  const catalogRequests = await interceptCatalogWithDuplicateCoordinate(page);
  await openMap(page);

  await expect(page.locator("[data-listing-id]")).toHaveCount(789);
  await expect(page.locator('[data-listing-id="900788"]')).toHaveCount(1);
  await expect(page.locator('[data-listing-id="900789"]')).toHaveCount(1);
  await expect.poll(() => page.getByTestId("mobility-map").locator(".marker-cluster").count())
    .toBeGreaterThan(0);

  const snapshot = await requestListingLayerSnapshot(page);
  expect(snapshot, "map container should expose its readonly actual-layer snapshot").not.toBeNull();
  if (snapshot === null) return;

  const mapState = await page.getByTestId("mobility-map").evaluate((container) => ({
    className: container.className,
    tileStatus: container.dataset.tileStatus,
    markerCount: container.querySelectorAll("[data-listing-pin-id]").length,
    clusterCount: container.querySelectorAll(".marker-cluster").length,
    childCount: container.childElementCount,
  }));
  expect(
    snapshot.state,
    `snapshot=${JSON.stringify(snapshot)} map=${JSON.stringify(mapState)} pageErrors=${JSON.stringify(pageErrors)} consoleErrors=${JSON.stringify(consoleErrors)}`,
  ).toBe("READY");
  expect(snapshot.members).toHaveLength(787);
  const expectedMembers = Array.from({ length: 787 }, (_, offset) => {
    const index = offset + 1;
    const lat = index === 2 ? 10.1002 : 10.1 + (index % 40) * 0.0002;
    const lng = index === 2 ? 105.1 : 105.1 + Math.floor(index / 40) * 0.0002;
    return { id: 900_000 + index, lat, lng };
  });
  expect(snapshot.members).toEqual(expectedMembers);
  expect(new Set(snapshot.members.map(({ id }) => id)).size).toBe(787);
  expect(snapshot.members.filter(({ id }) => id === 900_788 || id === 900_789)).toEqual([]);
  expect(snapshot.members[0].lat).toBe(snapshot.members[1].lat);
  expect(snapshot.members[0].lng).toBe(snapshot.members[1].lng);
  const completedRequests = catalogRequests.completedRequests();
  expect(completedRequests.every(({ size }) => size === 100)).toBe(true);
  expect(completedRequests.map(({ page }) => page).sort((left, right) => (left ?? 0) - (right ?? 0)))
    .toEqual([1, 2, 3, 4, 5, 6, 7, 8]);
  const failedRequests = catalogRequests.failedRequests();
  expect(failedRequests.length).toBeLessThanOrEqual(1);
  expect(failedRequests.every(({ page, size, failureText }) =>
    page === 1 && size === 100 && /ERR_ABORTED|ERR_CANCELED/.test(failureText ?? ""),
  )).toBe(true);
  expect(mobility.requests.some(({ path }) => path.includes("/listings/nearby"))).toBe(false);
});
test("list_selection_reveals_clustered_listing_and_keeps_selection_overlay_stable", async ({ page, mobility }) => {
  const pageErrors: string[] = [];
  page.on("pageerror", (error) => pageErrors.push(error.message));
  mobility.setCatalogTotal(789);
  await interceptCatalogWithDuplicateCoordinate(page);
  await openMap(page);
  await waitForListingLayerReady(page);
  const snapshotBeforeSelection = await requestListingLayerSnapshot(page);
  const map = page.getByTestId("mobility-map");
  const row = page.locator('[data-listing-id="900001"]');
  await row.click();
  await expect(row).toHaveAttribute("aria-pressed", "true");

  const marker = map.locator('[data-selection-overlay-id="900001"]');
  const popup = map.locator(".leaflet-popup-content");
  await expect(marker).toBeVisible();
  await expect(marker).toHaveAttribute("role", "button");
  await expect(marker).toHaveAttribute("tabindex", "0");
  await expect(marker).toHaveAttribute("data-lat", "10.1002");
  await expect(marker).toHaveAttribute("data-lng", "105.1");
  await expect(popup).toContainText("Tin fixture thiếu diện tích");

  const readRevealState = () => map.evaluate((container) => {
    const markerSelector = '[data-selection-overlay-id="900001"]';
    const currentMarker = container.querySelector<HTMLElement>(markerSelector);
    const popupElement = container.querySelector<HTMLElement>(".leaflet-popup-content");
    const markerStyle = currentMarker ? getComputedStyle(currentMarker) : null;
    const markerRect = currentMarker?.getBoundingClientRect();
    const popupStyle = popupElement ? getComputedStyle(popupElement) : null;
    const popupRect = popupElement?.getBoundingClientRect();
    return {
      markerCount: container.querySelectorAll(markerSelector).length,
      markerConnected: currentMarker?.isConnected ?? false,
      markerInMap: currentMarker ? container.contains(currentMarker) : false,
      markerId: currentMarker?.getAttribute("data-selection-overlay-id") ?? null,
      selectedFill: currentMarker?.querySelector("path")?.getAttribute("fill") ?? null,
      markerVisible: Boolean(
        currentMarker &&
        markerStyle &&
        markerRect &&
        markerStyle.display !== "none" &&
        markerStyle.visibility !== "hidden" &&
        Number(markerStyle.opacity) > 0 &&
        markerRect.width > 0 &&
        markerRect.height > 0,
      ),
      popupText: popupElement?.textContent?.trim() ?? null,
      popupVisible: Boolean(
        popupElement &&
        popupStyle &&
        popupRect &&
        popupStyle.display !== "none" &&
        popupStyle.visibility !== "hidden" &&
        Number(popupStyle.opacity) > 0 &&
        popupRect.width > 0 &&
        popupRect.height > 0,
      ),
    };
  });
  const selectedMarkerHandle = await marker.elementHandle();
  expect(selectedMarkerHandle).not.toBeNull();
  const atReveal = await readRevealState();
  await page.waitForTimeout(100);
  const after100ms = await readRevealState();
  await page.waitForTimeout(900);
  const after1s = await readRevealState();

  for (const [when, state] of [
    ["callback", atReveal],
    ["+100ms", after100ms],
    ["+1s", after1s],
  ] as const) {
    expect(
      state,
      `selected marker and popup must remain stable at ${when}`,
    ).toMatchObject({
      markerCount: 1,
      markerConnected: true,
      markerInMap: true,
      markerId: "900001",
      selectedFill: "#0f766e",
      markerVisible: true,
      popupText: expect.stringContaining("Tin fixture thiếu diện tích"),
      popupVisible: true,
    });
    expect(selectedMarkerHandle).not.toBeNull();
    expect(
      await selectedMarkerHandle!.evaluate((original, current) => original === current, await marker.elementHandle()),
      `selected overlay DOM node must remain the same at ${when}`,
    ).toBe(true);
  }
  await expect(marker).toBeVisible();
  await expect.poll(async () => marker.evaluate((element) => {
    const mapElement = element.closest('[data-testid="mobility-map"]');
    if (!mapElement) return false;
    const markerRect = element.getBoundingClientRect();
    const mapRect = mapElement.getBoundingClientRect();
    const markerX = markerRect.left + markerRect.width / 2;
    const markerY = markerRect.top + markerRect.height / 2;
    const mapX = mapRect.left + mapRect.width / 2;
    const mapY = mapRect.top + mapRect.height / 2;
    return Math.abs(markerX - mapX) < 100 && Math.abs(markerY - mapY) < 80;
  })).toBe(true);

  const sidebar = page.getByRole("complementary", { name: "Danh sách tin" });
  const scrollContainer = sidebar.locator("div.overflow-y-auto").last();
  await scrollContainer.evaluate((element) => {
    element.scrollTop = element.scrollHeight;
  });
  await expect(marker).toBeVisible();
  await marker.click();
  await expect(row).toBeInViewport({ ratio: 0.5 });
  await marker.focus();
  await marker.press("Enter");
  await expect(row).toBeInViewport({ ratio: 0.5 });

  const snapshotAfterSelection = await requestListingLayerSnapshot(page);
  expect(snapshotAfterSelection).toEqual(snapshotBeforeSelection);
  const snapshot = await requestListingLayerSnapshot(page);
  expect(snapshot?.state).toBe("READY");
  expect(snapshot?.members).toHaveLength(787);
  expect(mobility.requests.some(({ path }) => path === "/api/mobility/routes" || path === "/api/mobility/nearby")).toBe(false);
  expect(pageErrors).toEqual([]);
});
// End of selective map-reuse regression coverage.
test("map_selection_scrolls_and_selects_catalog_row", async ({ page, mobility }) => {
  mobility.setCatalogTotal(789);
  await interceptCatalogWithDuplicateCoordinate(page);
  await openMap(page);
  await waitForListingLayerReady(page);
  const snapshotBeforeSelection = await requestListingLayerSnapshot(page);

  const map = page.getByTestId("mobility-map");
  const sidebar = page.getByRole("complementary", { name: "Danh sách tin" });
  const scrollContainer = sidebar.locator("div.overflow-y-auto").last();
  const readMapInteractionState = () => map.evaluate((container) => ({
    pins: Array.from(container.querySelectorAll<HTMLElement>("[data-listing-pin-id]"))
      .map((pin) => pin.getAttribute("data-listing-pin-id")),
    clusters: Array.from(container.querySelectorAll<HTMLElement>(".marker-cluster"))
      .map((cluster) => {
        const bounds = cluster.getBoundingClientRect();
        return {
          markup: cluster.outerHTML,
          bounds: [bounds.x, bounds.y, bounds.width, bounds.height],
        };
      }),
  }));

  let selectedId: string | null = null;
  let scrollBeforeSelection = 0;
  while (selectedId === null) {
    const visiblePins = map.locator("[data-listing-pin-id]");
    const visiblePinCount = await visiblePins.count();
    await scrollContainer.evaluate((element) => {
      element.scrollTop = element.scrollHeight;
    });

    for (let index = 0; index < visiblePinCount; index += 1) {
      const pin = visiblePins.nth(index);
      if (!(await pin.isVisible())) continue;
      const candidateId = await pin.getAttribute("data-listing-pin-id");
      if (!candidateId) continue;
      const candidateRowVisible = await scrollContainer.evaluate((element, listingId) => {
        const row = element.querySelector<HTMLElement>(`[data-listing-id="${listingId}"]`);
        if (!row) return false;
        const rowBounds = row.getBoundingClientRect();
        const containerBounds = element.getBoundingClientRect();
        return rowBounds.bottom > containerBounds.top && rowBounds.top < containerBounds.bottom;
      }, candidateId);
      if (candidateRowVisible) continue;
      const pinHandle = await pin.elementHandle();
      if (!pinHandle) continue;
      const stayedConnected = await pinHandle.evaluate((element) => new Promise<boolean>((resolve) => {
        let stableFrames = 0;
        const check = () => {
          if (!element.isConnected) {
            resolve(false);
            return;
          }
          stableFrames += 1;
          if (stableFrames >= 12) {
            resolve(true);
            return;
          }
          requestAnimationFrame(check);
        };
        requestAnimationFrame(check);
      }));
      if (!stayedConnected) continue;
      const scrollBeforeClick = await scrollContainer.evaluate((element) => element.scrollTop);
      const clicked = await pin.click({ timeout: 1_500 }).then(() => true).catch(() => false);
      if (!clicked) continue;
      const selected = await page.waitForFunction((listingId) =>
        document.querySelector(`[data-listing-id="${listingId}"]`)?.getAttribute("aria-pressed") === "true",
      candidateId, { timeout: 1_500 }).then(() => true).catch(() => false);
      if (!selected) continue;
      scrollBeforeSelection = scrollBeforeClick;
      selectedId = candidateId;
      break;
    }
    if (selectedId !== null) break;

    const clusterButton = map.getByRole("button", { name: /^\d+$/ }).first();
    await expect(clusterButton, "cluster navigation should expose an accessible control until an original pin can be selected").toBeVisible();
    const stateBeforeClusterClick = await readMapInteractionState();
    await clusterButton.click();
    await expect.poll(readMapInteractionState).not.toEqual(stateBeforeClusterClick);
  }

  expect(selectedId, "cluster navigation should expose and click an original listing pin").not.toBeNull();
  const selectedRow = page.locator(`[data-listing-id="${selectedId}"]`);
  expect(scrollBeforeSelection).toBeGreaterThan(0);

  await expect(selectedRow).toHaveAttribute("aria-pressed", "true");
  await expect(selectedRow).toBeInViewport({ ratio: 0.5 });
  const selectedOverlay = map.locator(`[data-selection-overlay-id="${selectedId}"]`);
  await expect(selectedOverlay).toBeVisible();
  await expect.poll(() => scrollContainer.evaluate((element) => element.scrollTop))
    .toBeLessThan(scrollBeforeSelection);
  expect(await requestListingLayerSnapshot(page)).toEqual(snapshotBeforeSelection);
  expect(mobility.requests.some(({ path }) => path === "/api/mobility/routes" || path === "/api/mobility/nearby")).toBe(false);
});

test("missing_position_selects_detail_without_fly_or_provider_call", async ({ page, mobility }) => {
  mobility.setCatalogTotal(789);
  await interceptCatalogWithDuplicateCoordinate(page);
  await openMap(page);
  await expect.poll(async () => (await requestListingLayerSnapshot(page))?.state).toBe("READY");

  const map = page.getByTestId("mobility-map");
  const mapPane = map.locator(".leaflet-map-pane");
  const paneStyleBefore = await mapPane.getAttribute("style");
  const row = page.locator('[data-listing-id="900788"]');
  await row.click();

  await expect(row).toHaveAttribute("aria-pressed", "true");
  await expect(page.getByText("Tin chưa có tọa độ; vẫn giữ trong danh sách nhưng không đặt ghim.")).toBeVisible();
  await expect(page.getByRole("link", { name: "Xem tin gốc" })).toHaveAttribute(
    "href",
    "https://source.example.test/listing/788",
  );
  await expect(map.locator('[data-listing-pin-id="900788"]')).toHaveCount(0);
  await expect.poll(() => mapPane.getAttribute("style")).toBe(paneStyleBefore);
  expect(mobility.requests.some(({ path }) => path === "/api/mobility/routes" || path === "/api/mobility/nearby")).toBe(false);
});

test("popup_uses_safe_text_and_rejects_unsafe_source_url", async ({ page, mobility }) => {
  await interceptCatalogWithHostilePopupContent(page);
  await openMap(page, 3);
  await waitForListingLayerReady(page);
  await page.locator('[data-listing-id="900001"]').click();

  const popup = page.locator(".leaflet-popup-content");
  await expect(popup).toContainText('<img src="https://hostile.example.test/title.png" onerror="window.__mapPopupInjected=true">');
  await expect(popup).toContainText("Giá chưa rõ");
  await expect(popup).toContainText("hostile address");
  await expect(popup).toContainText("Vị trí gần đúng; cần xác nhận địa điểm và lối vào.");
  await expect(popup).toContainText("Nguồn tọa độ: SYNTHETIC_FIXTURE");
  await expect(popup.locator("img, svg, script")).toHaveCount(0);
  await expect(popup.locator("a")).toHaveCount(0);
  await expect(popup.locator('a[href^="javascript:"]')).toHaveCount(0);
  expect(await page.evaluate(() => (window as Window & { __mapPopupInjected?: boolean }).__mapPopupInjected)).toBeUndefined();
  expect(mobility.externalAttempts).toEqual([]);
});

test("popup_formats_price_and_links_to_safe_source_url", async ({ page, mobility }) => {
  mobility.setCatalogTotal(789);
  await interceptCatalogWithDuplicateCoordinate(page);
  await openMap(page);
  await waitForListingLayerReady(page);
  await page.locator('[data-listing-id="900001"]').click();

  const popup = page.locator(".leaflet-popup-content");
  await expect(popup).toContainText("Tin fixture thiếu diện tích");
  await expect(popup).toContainText("2.500.001 đ/tháng");
  await expect(popup).toContainText("Địa chỉ fixture 1");
  await expect(popup).toContainText("Vị trí gần đúng; cần xác nhận địa điểm và lối vào.");
  const sourceLink = popup.getByRole("link", { name: "Xem tin gốc" });
  await expect(sourceLink).toHaveAttribute("href", "https://source.example.test/listing/1");
  await expect(sourceLink).toHaveAttribute("target", "_blank");
  await expect(sourceLink).toHaveAttribute("rel", "noopener noreferrer");
  expect(mobility.externalAttempts).toEqual([]);
});

test("snapshot_reader_reports_only_actual_group_members", async () => {
  const provider = (await import("../src/components/mobility/leaflet-map-provider")) as unknown as {
    readListingLayerSnapshot?: (
      group: unknown,
      generation: number,
      markerClass: unknown,
    ) => ListingLayerSnapshot;
  };
  expect(typeof provider.readListingLayerSnapshot).toBe("function");
  if (typeof provider.readListingLayerSnapshot !== "function") return;

  class TestListingMarker {
    readonly listingId!: number;

    constructor(
      id: number,
      private readonly lat: number,
      private readonly lng: number,
    ) {
      Object.defineProperty(this, "listingId", {
        value: id,
        enumerable: true,
        writable: false,
        configurable: false,
      });
    }

    getLatLng() {
      return { lat: this.lat, lng: this.lng };
    }
  }

  const group = {
    getLayers: () => [
      new TestListingMarker(17, 10.1002, 105.1),
      new TestListingMarker(4, 10.1002, 105.1),
    ],
  };

  const snapshot = provider.readListingLayerSnapshot(
    group,
    12,
    TestListingMarker,
  );
  expect(snapshot).toEqual({
    generation: 12,
    state: "READY",
    members: [
      { id: 4, lat: 10.1002, lng: 105.1 },
      { id: 17, lat: 10.1002, lng: 105.1 },
    ],
  });
});

test("snapshot_reader_rejects_foreign_or_invalid_group_members", async () => {
  const provider = (await import("../src/components/mobility/leaflet-map-provider")) as unknown as {
    readListingLayerSnapshot?: (
      group: unknown,
      generation: number,
      markerClass: unknown,
    ) => ListingLayerSnapshot;
  };
  expect(typeof provider.readListingLayerSnapshot).toBe("function");
  if (typeof provider.readListingLayerSnapshot !== "function") return;

  class TestListingMarker {
    readonly listingId!: number;

    constructor(private readonly lat: number, private readonly lng: number) {
      Object.defineProperty(this, "listingId", {
        value: 1,
        enumerable: true,
        writable: false,
        configurable: false,
      });
    }

    getLatLng() {
      return { lat: this.lat, lng: this.lng };
    }
  }

  const invalidGroups = [
    { getLayers: () => [new TestListingMarker(10.1, 105.1), {}] },
    { getLayers: () => [new TestListingMarker(Number.NaN, 105.1)] },
  ];
  for (const group of invalidGroups) {
    expect(
      provider.readListingLayerSnapshot(group, 3, TestListingMarker),
    ).toEqual({ generation: 3, state: "UNAVAILABLE", members: [] });
  }
});

test("keyword_filter_matches_unaccented_title_and_address_without_catalog_refetch", async ({ page, mobility }) => {
  mobility.setCatalogTotal(789);
  const catalogRequests = await interceptCatalogForViewControls(page);
  await openMap(page);
  await waitForListingLayerReady(page);
  const map = page.getByTestId("mobility-map");

  await expect(page.getByTestId("filtered-count")).toContainText("789");
  const originalIds = await page.locator("[data-listing-id]").evaluateAll((rows) =>
    rows.map((row) => row.getAttribute("data-listing-id")),
  );
  expect(originalIds.slice(0, 4)).toEqual(["900001", "900004", "900003", "900002"]);
  const initialRequestCount = catalogRequests();
  const originalSnapshot = await requestListingLayerSnapshot(page);
  expect(originalSnapshot?.members).toHaveLength(787);

  const search = page.getByLabel("Tìm tin theo tên hoặc địa chỉ", { exact: true });
  await expect(search).toBeVisible();
  await search.fill("duong 3/2");
  await expect(page.getByTestId("catalog-count")).toHaveText("789 tin");
  await expect(page.getByTestId("filtered-count")).toContainText("2");
  await expect(page.locator("[data-listing-id]")).toHaveCount(2);
  expect(await page.locator("[data-listing-id]").evaluateAll((rows) =>
    rows.map((row) => row.getAttribute("data-listing-id")),
  )).toEqual(["900001", "900002"]);
  const filteredSnapshot = await requestListingLayerSnapshot(page);
  expect(filteredSnapshot?.state).toBe("READY");
  expect(filteredSnapshot?.members.map(({ id }) => id)).toEqual([900_001, 900_002]);

  await search.fill("");
  await expect(page.getByTestId("filtered-count")).toContainText("789");
  await expect(page.locator("[data-listing-id]")).toHaveCount(789);
  const restoredSnapshot = await requestListingLayerSnapshot(page);
  expect(restoredSnapshot?.members).toHaveLength(787);
  expect(restoredSnapshot?.members.map(({ id }) => id)).toEqual(
    originalSnapshot?.members.map(({ id }) => id),
  );
  expect(catalogRequests()).toBe(initialRequestCount);
  expect(mobility.requests.some(({ path }) => path === "/api/mobility/routes" || path === "/api/mobility/nearby")).toBe(false);
  await expect(map).toBeVisible();
});

test("price_sort_keeps_null_last_ties_and_actual_map_membership", async ({ page, mobility }) => {
  mobility.setCatalogTotal(789);
  const catalogRequests = await interceptCatalogForViewControls(page);
  await openMap(page);
  await waitForListingLayerReady(page);
  const map = page.getByTestId("mobility-map");
  const originalSnapshot = await requestListingLayerSnapshot(page);
  const sort = page.getByLabel("Sắp xếp giá", { exact: true });
  await expect(sort).toBeVisible();

  await sort.selectOption("price_asc");
  let ids = await page.locator("[data-listing-id]").evaluateAll((rows) =>
    rows.map((row) => row.getAttribute("data-listing-id")),
  );
  expect(ids.slice(0, 3)).toEqual(["900003", "900002", "900004"]);
  expect(ids.slice(-2)).toEqual(["900788", "900789"]);

  await sort.selectOption("price_desc");
  ids = await page.locator("[data-listing-id]").evaluateAll((rows) =>
    rows.map((row) => row.getAttribute("data-listing-id")),
  );
  expect(ids.slice(-2)).toEqual(["900788", "900789"]);
  expect(ids.indexOf("900002")).toBeLessThan(ids.indexOf("900004"));
  expect(ids.indexOf("900004")).toBeLessThan(ids.indexOf("900003"));

  await sort.selectOption("original");
  ids = await page.locator("[data-listing-id]").evaluateAll((rows) =>
    rows.map((row) => row.getAttribute("data-listing-id")),
  );
  expect(ids.slice(0, 4)).toEqual(["900001", "900004", "900003", "900002"]);
  const snapshotAfterSorts = await requestListingLayerSnapshot(page);
  expect(snapshotAfterSorts).toEqual(originalSnapshot);
  expect(snapshotAfterSorts?.state).toBe("READY");
  const positionedListIds = ids
    .map(Number)
    .filter((id) => id !== 900_788 && id !== 900_789)
    .sort((left, right) => left - right);
  expect(positionedListIds).toEqual(snapshotAfterSorts?.members.map(({ id }) => id));
  expect(catalogRequests()).toBe(8);
  expect(mobility.requests.some(({ path }) => path === "/api/mobility/routes" || path === "/api/mobility/nearby")).toBe(false);
  await expect(map).toBeVisible();
});

test("filtered_out_selection_synchronously_cancels_route_and_nearby", async ({ page, mobility }) => {
  mobility.setCatalogTotal(789);
  const catalogRequests = await interceptCatalogForViewControls(page);
  await openMap(page);
  await waitForListingLayerReady(page);
  await page.locator('[data-listing-id="900003"]').click();
  await expect(page.locator('[data-listing-id="900003"]')).toHaveAttribute("aria-pressed", "true");
  const map = page.getByTestId("mobility-map");
  const selectionOverlay = map.locator('[data-selection-overlay-id="900003"]');
  await expect(selectionOverlay).toBeVisible();
  const pane = map.locator(".leaflet-map-pane");
  await waitForStableMapPane(pane);
  const paneStyleBeforeFilter = await pane.getAttribute("style");

  const staleRoute = mobility.holdNextRoute((request) => request.listing_id === 900_003);
  await page.getByRole("button", { name: "Tính tuyến tới khu đã chọn" }).click();
  await staleRoute.seen;
  const staleNearby = mobility.holdNextNearby((request) => request.listing_id === 900_003);
  await page.getByRole("button", { name: "Tìm tiện ích quanh tin" }).click();
  await staleNearby.seen;
  await expect(page.getByTestId("route-result-khu_i")).toHaveAttribute("data-status", "PENDING");
  await expect(page.getByTestId("nearby-result")).toHaveAttribute("data-status", "PENDING");

  const search = page.getByLabel("Tìm tin theo tên hoặc địa chỉ", { exact: true });
  await expect(search).toBeVisible();
  await search.fill("duong 3/2");
  await expect(page.locator('[data-listing-id="900003"]')).toHaveCount(0);
  await expect(selectionOverlay).toHaveCount(0);
  await expect(page.getByTestId("route-result-khu_i")).toHaveCount(0);
  await expect(page.getByTestId("nearby-result")).toHaveCount(0);
  await expect(page.getByRole("region", { name: "Chi tiết tin được chọn" })).toContainText("Chọn một tin");
  const paneStyleAfterFilter = await pane.getAttribute("style");
  expect(paneStyleAfterFilter).toBe(paneStyleBeforeFilter);
  await expect(page.locator('[data-listing-id="900001"]')).toHaveCount(1);
  expect(catalogRequests()).toBe(8);

  staleRoute.release({ status: 503, body: { detail: "stale route fixture" } });
  staleNearby.release({ status: 503, body: { detail: "stale nearby fixture" } });
  await Promise.all([staleRoute.settled, staleNearby.settled]);
  await expect(page.getByTestId("route-result-khu_i")).toHaveCount(0);
  await expect(page.getByTestId("nearby-result")).toHaveCount(0);
  expect(await pane.getAttribute("style")).toBe(paneStyleAfterFilter);
  expect(mobility.requests.filter(({ path }) => path === "/api/mobility/routes")).toHaveLength(1);
  expect(mobility.requests.filter(({ path }) => path === "/api/mobility/nearby")).toHaveLength(1);
});

test("filtering_out_rapid_latest_selection_stops_its_inflight_map_fly", async ({ page, mobility }) => {
  mobility.setCatalogTotal(789);
  const catalogRequests = await interceptCatalogForViewControls(page);
  await openMap(page);
  await waitForListingLayerReady(page);

  const map = page.getByTestId("mobility-map");
  const instrumentationInstalled = await map.evaluate((container) => {
    const testWindow = window as MapReuseTestWindow;
    const mapPrototype = testWindow.L?.Map?.prototype;
    const clusterPrototype = testWindow.L?.MarkerClusterGroup?.prototype;
    if (!mapPrototype?.stop || !clusterPrototype?.zoomToShowLayer) return false;

    const originalStop = mapPrototype.stop;
    const originalReveal = clusterPrototype.zoomToShowLayer;
    const counters = { zoomToShowCalls: 0, mapStopCalls: 0 };
    mapPrototype.stop = function (this: unknown, ...args: unknown[]) {
      counters.mapStopCalls += 1;
      return originalStop.apply(this, args);
    };
    clusterPrototype.zoomToShowLayer = function (this: unknown, ...args: unknown[]) {
      counters.zoomToShowCalls += 1;
      return originalReveal.apply(this, args);
    };
    testWindow.__mobilityMapReuseCounters = counters;
    testWindow.__restoreMobilityMapReuseHooks = () => {
      mapPrototype.stop = originalStop;
      clusterPrototype.zoomToShowLayer = originalReveal;
      delete testWindow.__mobilityMapReuseCounters;
      delete testWindow.__restoreMobilityMapReuseHooks;
    };
    return container.isConnected;
  });
  expect(instrumentationInstalled).toBe(true);

  const firstRow = page.locator('[data-listing-id="900001"]');
  const latestRow = page.locator('[data-listing-id="900004"]');
  try {
    await firstRow.click();
    await latestRow.click();
    await expect(latestRow).toHaveAttribute("aria-pressed", "true");
    const stopCallsBeforeFilter = await map.evaluate(() => {
      const testWindow = window as MapReuseTestWindow;
      return testWindow.__mobilityMapReuseCounters?.mapStopCalls ?? 0;
    });

    const search = page.getByLabel("Tìm tin theo tên hoặc địa chỉ", { exact: true });
    await search.fill("duong 3/2");
    await expect(latestRow).toHaveCount(0);
    await expect(map.locator('[data-selection-overlay-id="900004"]')).toHaveCount(0);
    await expect.poll(async () => (await requestListingLayerSnapshot(page))?.members.length).toBe(2);

    const counters = await map.evaluate(() => {
      const testWindow = window as MapReuseTestWindow;
      return testWindow.__mobilityMapReuseCounters ?? null;
    });
    expect(counters, "test instrumentation should remain installed").not.toBeNull();
    expect(counters, JSON.stringify(counters)).toMatchObject({ zoomToShowCalls: 0 });
    expect(counters?.mapStopCalls).toBeGreaterThan(stopCallsBeforeFilter);
    expect(catalogRequests()).toBe(8);
    expect(mobility.requests.some(({ path }) => path === "/api/mobility/routes" || path === "/api/mobility/nearby")).toBe(false);
  } finally {
    await map.evaluate(() => {
      const testWindow = window as MapReuseTestWindow;
      testWindow.__restoreMobilityMapReuseHooks?.();
    });
  }
});

test("sidebar_resize_keeps_map_layers_and_selection_across_mobile_and_keyboard_toggle", async ({ page, mobility }, testInfo) => {
  mobility.setCatalogTotal(789);
  const catalogRequests = await interceptCatalogForViewControls(page);
  await page.setViewportSize({ width: 1440, height: 960 });
  await openMap(page);
  await waitForListingLayerReady(page);
  const catalogRequestsAfterLoad = catalogRequests();
  expect(catalogRequestsAfterLoad).toBeGreaterThanOrEqual(8);

  const map = page.getByTestId("mobility-map");
  const mapHandle = await map.elementHandle();
  expect(mapHandle).not.toBeNull();
  const row = page.locator('[data-listing-id="900001"]');
  await row.click();
  await expect(row).toHaveAttribute("aria-pressed", "true");
  await expect(map.locator('[data-selection-overlay-id="900001"]')).toBeVisible();
  const snapshot = await requestListingLayerSnapshot(page);
  expect(snapshot?.members).toHaveLength(787);
  await expect(map.locator("[data-campus-id]")).toHaveCount(3);

  const desktopShot = resolve(
    process.cwd(),
    "../../.superpowers/sdd/2026-10-05-open-mobility-map-reuse-plan/mobility-view-controls-desktop.png",
  );
  await page.screenshot({ path: desktopShot, fullPage: true });
  await testInfo.attach("mobility-view-controls-desktop", {
    path: desktopShot,
    contentType: "image/png",
  });

  const sidebar = page.getByRole("complementary", { name: "Danh sách tin" });
  const widthBeforeCollapse = await map.evaluate((element) => element.getBoundingClientRect().width);
  const collapse = page.getByRole("button", { name: "Thu gọn danh sách tin", exact: true });
  await collapse.focus();
  await collapse.press("Enter");
  await expect(sidebar).toBeHidden();
  await expect(page.getByRole("button", { name: "Mở danh sách tin", exact: true })).toHaveAttribute(
    "aria-expanded",
    "false",
  );
  await expect(map.locator('[data-selection-overlay-id="900001"]')).toBeVisible();
  await expect(map.locator("[data-campus-id]")).toHaveCount(3);
  expect(await requestListingLayerSnapshot(page)).toEqual(snapshot);
  const widthAfterCollapse = await map.evaluate((element) => element.getBoundingClientRect().width);
  expect(widthAfterCollapse).toBeGreaterThan(widthBeforeCollapse);
  expect(await mapHandle!.evaluate((original, current) => original === current, await map.elementHandle())).toBe(true);

  await page.setViewportSize({ width: 390, height: 844 });
  await expect(map).toBeVisible();
  const mobileSize = await map.evaluate((element) => {
    const rect = element.getBoundingClientRect();
    return { width: rect.width, height: rect.height };
  });
  expect(mobileSize.width).toBeGreaterThan(0);
  expect(mobileSize.height).toBeGreaterThan(0);
  const mobileShot = resolve(
    process.cwd(),
    "../../.superpowers/sdd/2026-10-05-open-mobility-map-reuse-plan/mobility-view-controls-mobile.png",
  );
  await page.screenshot({ path: mobileShot, fullPage: true });
  await testInfo.attach("mobility-view-controls-mobile", {
    path: mobileShot,
    contentType: "image/png",
  });

  const expand = page.getByRole("button", { name: "Mở danh sách tin", exact: true });
  await expand.focus();
  await expand.press("Space");
  await expect(sidebar).toBeVisible();
  await expect(row).toHaveAttribute("aria-pressed", "true");
  await expect(map.locator('[data-selection-overlay-id="900001"]')).toBeVisible();

  await page.setViewportSize({ width: 1440, height: 960 });
  await expect(map).toBeVisible();
  expect(await mapHandle!.evaluate((original, current) => original === current, await map.elementHandle())).toBe(true);
  expect(await requestListingLayerSnapshot(page)).toEqual(snapshot);
  expect(catalogRequests()).toBe(catalogRequestsAfterLoad);
  expect(mobility.requests.some(({ path }) => path === "/api/mobility/routes" || path === "/api/mobility/nearby")).toBe(false);
});

test("filter_clear_before_mobility_map_component_chunk_keeps_only_final_visible_members", async ({ page, mobility }) => {
  mobility.setCatalogTotal(789);
  const catalogRequests = await interceptCatalogForViewControls(page);
  let releaseProvider!: () => void;
  let markProviderSettled!: () => void;
  let providerImportStarted = false;
  let heldChunkUrl = "";
  const providerHold = new Promise<void>((resolve) => {
    releaseProvider = resolve;
  });
  const providerSettled = new Promise<void>((resolve) => {
    markProviderSettled = resolve;
  });
  let firstProviderRequest = true;
  await page.route("**/*MobilityMap_tsx.js", async (route) => {
    if (firstProviderRequest) {
      firstProviderRequest = false;
      providerImportStarted = true;
      heldChunkUrl = route.request().url();
      await providerHold;
    }
    try {
      await route.continue();
    } catch {
      // Navigation may cancel an import request; the race still settles for the test.
    } finally {
      markProviderSettled();
    }
  });

  try {
    await page.goto("/map");
    await expect(page.getByRole("heading", { name: "Bản đồ di chuyển", level: 1 })).toBeVisible();
    await expect.poll(() => providerImportStarted, { timeout: 10_000 }).toBe(true);
    expect(heldChunkUrl).toContain("MobilityMap_tsx.js");
    await expect(page.getByTestId("catalog-count")).toHaveText("789 tin");
    const search = page.getByLabel("Tìm tin theo tên hoặc địa chỉ", { exact: true });
    await expect(search).toBeVisible();
    await search.fill("duong 3/2");
    await expect(page.locator("[data-listing-id]")).toHaveCount(2);
    await search.fill("");
    await expect(page.locator("[data-listing-id]")).toHaveCount(789);
    await search.fill("duong 3/2");
    await expect(page.locator("[data-listing-id]")).toHaveCount(2);
    expect(catalogRequests()).toBe(8);

    releaseProvider();
    await providerSettled;
    await waitForListingLayerReady(page);
    const snapshot = await requestListingLayerSnapshot(page);
    expect(snapshot?.members.map(({ id }) => id)).toEqual([900_001, 900_002]);
    expect(snapshot?.members).toHaveLength(2);
  } finally {
    releaseProvider();
  }
});

test("unmount_while_mobility_map_component_chunk_is_pending", async ({ page, mobility }) => {
  mobility.setCatalogTotal(789);
  const catalogRequests = await interceptCatalogForViewControls(page);
  const pageErrors: string[] = [];
  page.on("pageerror", (error) => pageErrors.push(error.message));
  let releaseProvider!: () => void;
  let markProviderSettled!: () => void;
  let providerImportStarted = false;
  let heldChunkUrl = "";
  const providerHold = new Promise<void>((resolve) => {
    releaseProvider = resolve;
  });
  const providerSettled = new Promise<void>((resolve) => {
    markProviderSettled = resolve;
  });
  let firstProviderRequest = true;
  await page.route("**/*MobilityMap_tsx.js", async (route) => {
    if (firstProviderRequest) {
      firstProviderRequest = false;
      providerImportStarted = true;
      heldChunkUrl = route.request().url();
      await providerHold;
    }
    try {
      await route.continue();
    } catch {
      // The current page may be gone before the held import continues.
    } finally {
      markProviderSettled();
    }
  });

  try {
    await page.goto("/map");
    await expect(page.getByRole("heading", { name: "Bản đồ di chuyển", level: 1 })).toBeVisible();
    await expect.poll(() => providerImportStarted, { timeout: 10_000 }).toBe(true);
    expect(heldChunkUrl).toContain("MobilityMap_tsx.js");
    await expect(page.getByTestId("catalog-count")).toHaveText("789 tin");
    await page.getByLabel("Tìm tin theo tên hoặc địa chỉ", { exact: true }).fill("duong 3/2");
    await expect(page.locator("[data-listing-id]")).toHaveCount(2);
    await page.getByRole("link", { name: "Trọ CTU, trang chủ" }).click();
    await expect(page.getByRole("heading", { name: "Trọ CTU", level: 1 })).toBeVisible();
    releaseProvider();
    await providerSettled;

    await page.goBack();
    await expect(page.getByRole("heading", { name: "Bản đồ di chuyển", level: 1 })).toBeVisible();
    await expect(page.getByTestId("catalog-count")).toHaveText("789 tin");
    await waitForListingLayerReady(page);
    const snapshot = await requestListingLayerSnapshot(page);
    expect(snapshot?.members).toHaveLength(787);
    expect(snapshot?.members.map(({ id }) => id)).toEqual(
      Array.from({ length: 787 }, (_, offset) => 900_001 + offset),
    );
    expect(catalogRequests()).toBeGreaterThanOrEqual(8);
    expect(pageErrors).toEqual([]);
  } finally {
    releaseProvider();
  }
});

test("filter_clear_while_leaflet_and_markercluster_imports_are_pending_keeps_final_members", async ({ page, mobility }) => {
  mobility.setCatalogTotal(789);
  const catalogRequests = await interceptCatalogForViewControls(page);
  const leafletChunk = await holdLocalChunk(
    page,
    "_app-pages-browser_node_modules_leaflet_dist_leaflet-src_js.js",
  );
  const markerClusterChunk = await holdLocalChunk(
    page,
    "_app-pages-browser_node_modules_leaflet_markercluster_dist_leaflet_markercluster-src_js.js",
  );

  try {
    await page.goto("/map", { waitUntil: "domcontentloaded" });
    await expect(page.getByRole("heading", { name: "Bản đồ di chuyển", level: 1 })).toBeVisible();
    const map = page.getByTestId("mobility-map");
    await expect(map).toBeVisible();
    await expect.poll(() => leafletChunk.requestUrl, { timeout: 10_000 })
      .toContain("_app-pages-browser_node_modules_leaflet_dist_leaflet-src_js.js");
    await expect(page.getByTestId("catalog-count")).toHaveText("789 tin");
    const catalogRequestsAfterLoad = catalogRequests();
    expect(catalogRequestsAfterLoad).toBeGreaterThanOrEqual(8);

    const search = page.getByLabel("Tìm tin theo tên hoặc địa chỉ", { exact: true });
    await search.fill("duong 3/2");
    await expect(page.locator("[data-listing-id]")).toHaveCount(2);
    await search.fill("");
    await expect(page.locator("[data-listing-id]")).toHaveCount(789);
    await expect.poll(async () => (await requestListingLayerSnapshot(page))?.state)
      .toBe("UNAVAILABLE");
    await expect(map).not.toHaveClass(/leaflet-container/);
    await expect(map.locator("[data-listing-pin-id]")).toHaveCount(0);

    leafletChunk.release();
    await leafletChunk.settled;
    await expect.poll(() => markerClusterChunk.requestUrl, { timeout: 10_000 })
      .toContain("_app-pages-browser_node_modules_leaflet_markercluster_dist_leaflet_markercluster-src_js.js");
    await expect.poll(async () => (await requestListingLayerSnapshot(page))?.state)
      .toBe("UNAVAILABLE");

    await search.fill("duong 3/2");
    await expect(page.locator("[data-listing-id]")).toHaveCount(2);
    await search.fill("");
    await expect(page.locator("[data-listing-id]")).toHaveCount(789);
    await search.fill("duong 3/2");
    await expect(page.locator("[data-listing-id]")).toHaveCount(2);
    await expect.poll(async () => (await requestListingLayerSnapshot(page))?.state)
      .toBe("UNAVAILABLE");
    expect(catalogRequests()).toBe(catalogRequestsAfterLoad);
    expect(mobility.requests.some(({ path }) => path === "/api/mobility/routes" || path === "/api/mobility/nearby")).toBe(false);

    markerClusterChunk.release();
    await markerClusterChunk.settled;
    await waitForListingLayerReady(page);
    const snapshot = await requestListingLayerSnapshot(page);
    expect(snapshot?.state).toBe("READY");
    const expectedMembers = [1, 2].map((index) => {
      const position = syntheticListing(index, 789).position;
      if (!position) throw new Error(`fixture listing ${index} unexpectedly lacks a position`);
      return { id: 900_000 + index, lat: position.lat, lng: position.lng };
    });
    expect(snapshot?.members).toEqual(expectedMembers);
    expect(catalogRequests()).toBe(catalogRequestsAfterLoad);
  } finally {
    leafletChunk.release();
    markerClusterChunk.release();
  }
});

test("unmount_while_leaflet_imports_are_pending_blocks_stale_init_and_remounts", async ({ page, mobility }) => {
  mobility.setCatalogTotal(789);
  const catalogRequests = await interceptCatalogForViewControls(page);
  const leafletChunk = await holdLocalChunk(
    page,
    "_app-pages-browser_node_modules_leaflet_dist_leaflet-src_js.js",
  );
  const markerClusterChunk = await holdLocalChunk(
    page,
    "_app-pages-browser_node_modules_leaflet_markercluster_dist_leaflet_markercluster-src_js.js",
  );
  const initGuardMutation = await installInitGuardMutation(page);
  const pageErrors: string[] = [];
  page.on("pageerror", (error) => pageErrors.push(error.message));

  try {
    await page.goto("/map", { waitUntil: "domcontentloaded" });
    await expect(page.getByRole("heading", { name: "Bản đồ di chuyển", level: 1 })).toBeVisible();
    const oldMap = page.getByTestId("mobility-map");
    await expect(oldMap).toBeVisible();
    await expect.poll(() => leafletChunk.requestUrl, { timeout: 10_000 })
      .toContain("_app-pages-browser_node_modules_leaflet_dist_leaflet-src_js.js");
    await expect(page.getByTestId("catalog-count")).toHaveText("789 tin");
    const oldMapHandle = await oldMap.elementHandle();
    expect(oldMapHandle).not.toBeNull();
    const documentTimeOrigin = await page.evaluate(() => performance.timeOrigin);
    expect(await requestListingLayerSnapshot(page)).toMatchObject({ state: "UNAVAILABLE", members: [] });

    leafletChunk.release();
    await leafletChunk.settled;
    await expect.poll(() => markerClusterChunk.requestUrl, { timeout: 10_000 })
      .toContain("_app-pages-browser_node_modules_leaflet_markercluster_dist_leaflet_markercluster-src_js.js");
    await expect.poll(async () => (await requestListingLayerSnapshot(page))?.state)
      .toBe("UNAVAILABLE");

    await page.evaluate(() => {
      const appWindow = window as MapReuseTestWindow;
      if (!appWindow.next?.router?.push) throw new Error("Next App Router test seam is unavailable");
      appWindow.next.router.push("/");
    });
    await expect(page.getByRole("heading", { name: "Trọ CTU", level: 1 })).toBeVisible();
    expect(await page.evaluate(() => performance.timeOrigin)).toBe(documentTimeOrigin);
    expect(await oldMapHandle!.evaluate((element) => element.isConnected)).toBe(false);

    markerClusterChunk.release();
    await markerClusterChunk.settled;
    await expect.poll(() => page.evaluate(() => {
      const appWindow = window as MapReuseTestWindow;
      return typeof appWindow.L?.MarkerClusterGroup?.prototype.zoomToShowLayer === "function";
    }), { timeout: 10_000 }).toBe(true);
    await page.evaluate(() => new Promise<void>((resolveFrame) => {
      requestAnimationFrame(() => resolveFrame());
    }));
    const staleContainerState = await oldMapHandle!.evaluate((element) => {
      let snapshot: ListingLayerSnapshot | null = null;
      element.dispatchEvent(new CustomEvent("mobility:listing-layer-snapshot", {
        detail: { respond(value: ListingLayerSnapshot) { snapshot = value; } },
      }));
      return {
        connected: element.isConnected,
        hasLeafletContainer: element.classList.contains("leaflet-container"),
        listingPinCount: element.querySelectorAll("[data-listing-pin-id]").length,
        snapshot,
      };
    });
    const mutatedGuard = process.env.P2UI_TEST_MUTATE_INIT_GUARD === "true";
    if (mutatedGuard) expect(initGuardMutation().applied, initGuardMutation().error ?? "guard mutation").toBe(true);
    expect(staleContainerState).toEqual({
      connected: false,
      hasLeafletContainer: false,
      listingPinCount: 0,
      snapshot: null,
    });

    await page.evaluate(() => {
      const appWindow = window as MapReuseTestWindow;
      if (!appWindow.next?.router?.push) throw new Error("Next App Router test seam is unavailable");
      appWindow.next.router.push("/map");
    });
    await expect(page.getByRole("heading", { name: "Bản đồ di chuyển", level: 1 })).toBeVisible();
    await expect(page.getByTestId("catalog-count")).toHaveText("789 tin");
    await waitForListingLayerReady(page);
    expect(await requestListingLayerSnapshot(page)).toMatchObject({
      state: "READY",
      members: Array.from({ length: 787 }, (_, offset) => ({ id: 900_001 + offset })),
    });
    expect(catalogRequests()).toBeGreaterThanOrEqual(16);
    expect(mobility.requests.some(({ path }) => path === "/api/mobility/routes" || path === "/api/mobility/nearby")).toBe(false);
    expect(pageErrors).toEqual([]);
  } finally {
    leafletChunk.release();
    markerClusterChunk.release();
  }
});

test("keyboard_on_unselected_original_pin_selects_details_and_scrolls_row", async ({ page, mobility }) => {
  mobility.setCatalogTotal(789);
  await interceptCatalogWithDuplicateCoordinate(page);
  await installKeyboardNoopMutation(page);
  await openMap(page);
  await waitForListingLayerReady(page);

  const map = page.getByTestId("mobility-map");
  const snapshotBefore = await requestListingLayerSnapshot(page);
  const sidebar = page.getByRole("complementary", { name: "Danh sách tin" });
  const scrollContainer = sidebar.locator("div.overflow-y-auto").last();
  await scrollContainer.evaluate((element) => {
    element.scrollTop = element.scrollHeight;
  });

  const readMapInteractionState = () => map.evaluate((container) => ({
    pins: Array.from(container.querySelectorAll<HTMLElement>("[data-listing-pin-id]"))
      .map((pin) => pin.getAttribute("data-listing-pin-id")),
    clusters: Array.from(container.querySelectorAll<HTMLElement>(".marker-cluster"))
      .map((cluster) => {
        const bounds = cluster.getBoundingClientRect();
        return { markup: cluster.outerHTML, bounds: [bounds.x, bounds.y, bounds.width, bounds.height] };
      }),
  }));
  let selectedPin: Locator | null = null;
  let selectedRow: Locator | null = null;
  let selectedId: string | null = null;
  let selectedPinHandle: Awaited<ReturnType<Locator["elementHandle"]>> | null = null;

  for (let attempt = 0; attempt < 12 && selectedPin === null; attempt += 1) {
    const visiblePins = map.locator("[data-listing-pin-id]");
    const pinCount = await visiblePins.count();
    for (let index = 0; index < pinCount; index += 1) {
      const candidate = visiblePins.nth(index);
      if (!(await candidate.isVisible())) continue;
      const id = await candidate.getAttribute("data-listing-pin-id");
      if (!id) continue;
      const row = page.locator(`[data-listing-id="${id}"]`);
      if (await row.getAttribute("aria-pressed") !== "false") continue;
      const pinnedCandidate = map.locator(`[data-listing-pin-id="${id}"]`);
      const [candidateHandle] = await pinnedCandidate.elementHandles();
      if (!candidateHandle) continue;
      const stable = await candidateHandle.evaluate((element) => new Promise<boolean>((resolveStable) => {
        let stableFrames = 0;
        const check = () => {
          if (!element.isConnected) {
            resolveStable(false);
            return;
          }
          stableFrames += 1;
          if (stableFrames >= 12) {
            resolveStable(true);
            return;
          }
          requestAnimationFrame(check);
        };
        requestAnimationFrame(check);
      }));
      if (!stable) continue;
      selectedPin = pinnedCandidate;
      selectedRow = row;
      selectedId = id;
      selectedPinHandle = candidateHandle;
      break;
    }
    if (selectedPin !== null) break;

    const clusterButton = map.getByRole("button", { name: /^\d+$/ }).first();
    await expect(clusterButton, "cluster navigation should reveal an original marker for keyboard selection").toBeVisible();
    const stateBefore = await readMapInteractionState();
    await clusterButton.click();
    await expect.poll(readMapInteractionState).not.toEqual(stateBefore);
  }

  expect(selectedPin, "an original, unselected listing pin should be keyboard reachable").not.toBeNull();
  expect(selectedRow).not.toBeNull();
  expect(selectedId).not.toBeNull();
  await expect(selectedRow!).toHaveAttribute("aria-pressed", "false");
  await expect(selectedRow!).not.toBeInViewport();
  expect(selectedPinHandle).not.toBeNull();
  expect(await selectedPinHandle!.evaluate((element) => element.isConnected)).toBe(true);
  await expect(selectedPin!).toHaveAttribute("data-listing-pin-id", selectedId!);
  await selectedPin!.focus();
  await expect(selectedPin!).toBeFocused();
  await selectedPin!.press("Enter");
  await expect(selectedRow!).toHaveAttribute("aria-pressed", "true");
  await expect(selectedRow!).toBeInViewport({ ratio: 0.5 });

  const overlay = map.locator(`[data-selection-overlay-id="${selectedId}"]`);
  await expect(overlay).toBeVisible();
  const title = await selectedRow!.locator("span").first().textContent();
  await expect(overlay).toHaveAttribute("aria-label", `Tin được chọn: ${title}`);
  await expect(page.getByRole("region", { name: "Chi tiết tin được chọn" }).last()
    .getByRole("heading", { name: title ?? "", exact: true })).toBeVisible();
  expect(await requestListingLayerSnapshot(page)).toEqual(snapshotBefore);
  expect(mobility.requests.some(({ path }) => path === "/api/mobility/routes" || path === "/api/mobility/nearby")).toBe(false);
});