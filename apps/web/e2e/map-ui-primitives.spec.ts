import { expect, test } from "@playwright/test";

const mapUiModulePath = "../src/lib/map-ui";

type DivIconOptions = {
  className?: string;
  html?: string;
  iconSize?: [number, number];
  iconAnchor?: [number, number];
  popupAnchor?: [number, number];
};

type LeafletModule = {
  divIcon(options: DivIconOptions): unknown;
};

type MapUiModule = {
  normalizeMapSearch(value: string | null | undefined): string;
  sortMapListingsByPrice<T extends { id: number; price: number | null }>(
    rows: readonly T[],
    order: "original" | "price_asc" | "price_desc",
  ): T[];
  createHousingIcon(leaflet: LeafletModule, selected: boolean): unknown;
  createCampusIcon(leaflet: LeafletModule): unknown;
  focusSelectedPosition(
    map: {
      flyTo(position: [number, number], zoom: number, options: { duration: number }): unknown;
      getZoom(): number;
    },
    position: [number, number] | null,
  ): void;
  observeMapResize(map: { getContainer(): Element; invalidateSize(): void }): () => void;
  scrollMapSelection(container: HTMLElement | null, listingId: number | null): void;
};

function isMissingMapUiModule(error: unknown): boolean {
  if (!(error instanceof Error)) return false;

  const code = (error as Error & { code?: unknown }).code;
  const message = error.message.replaceAll("\\", "/");
  return (
    (code === "ERR_MODULE_NOT_FOUND" || code === "MODULE_NOT_FOUND") &&
    message.includes("src/lib/map-ui")
  );
}

async function requireMapUi(): Promise<MapUiModule> {
  let helpers: MapUiModule | null;
  try {
    helpers = (await import(mapUiModulePath)) as MapUiModule;
  } catch (error) {
    if (!isMissingMapUiModule(error)) throw error;
    helpers = null;
  }

  expect(helpers, "the approved shared map UI helper module is missing").not.toBeNull();
  if (helpers === null) throw new Error("unreachable after the missing-helper assertion");
  return helpers;
}

test("shared_map_normalizes_vietnamese_title_and_address", async () => {
  const helpers = await requireMapUi();

  expect(helpers.normalizeMapSearch("Đường 3/2")).toBe("duong 3/2");
  expect(helpers.normalizeMapSearch("DUONG 3/2")).toBe("duong 3/2");
  expect(helpers.normalizeMapSearch(null)).toBe("");
  expect(helpers.normalizeMapSearch(undefined)).toBe("");
});

test("shared_price_sort_keeps_null_last_and_source_immutable", async () => {
  const helpers = await requireMapUi();
  const rows = [
    { id: 4, price: 1_000, title: "four" },
    { id: 1, price: null, title: "unknown one" },
    { id: 3, price: 0, title: "free" },
    { id: 2, price: 1_000, title: "two" },
    { id: 7, price: 3_000, title: "seven" },
    { id: 9, price: null, title: "unknown nine" },
  ];
  const originalIds = rows.map(({ id }) => id);

  const ascending = helpers.sortMapListingsByPrice(rows, "price_asc");
  const descending = helpers.sortMapListingsByPrice(rows, "price_desc");
  const unchanged = helpers.sortMapListingsByPrice(rows, "original");

  expect(ascending.map(({ id }) => id)).toEqual([3, 2, 4, 7, 1, 9]);
  expect(descending.map(({ id }) => id)).toEqual([7, 2, 4, 3, 1, 9]);
  expect(unchanged.map(({ id }) => id)).toEqual(originalIds);
  expect(unchanged).not.toBe(rows);
  expect(rows.map(({ id }) => id)).toEqual(originalIds);
  expect(ascending[1]).toBe(rows[3]);
  expect(descending[1]).toBe(rows[3]);
});

test("shared_pin_palette_has_selected_and_campus_shapes", async () => {
  const helpers = await requireMapUi();
  const captured: DivIconOptions[] = [];
  const leaflet = {
    divIcon(options: DivIconOptions) {
      captured.push(options);
      return options;
    },
  };

  helpers.createHousingIcon(leaflet, false);
  helpers.createHousingIcon(leaflet, true);
  helpers.createCampusIcon(leaflet);

  const [housing, selected, campus] = captured;
  expect(housing.html).toContain('fill="#e11d48"');
  expect(selected.html).toContain('fill="#0f766e"');
  expect(selected.html).toContain('stroke="#ffffff"');
  expect(campus.html).toContain('fill="#1d4ed8"');
  expect(campus.html).toContain('fill="#fde047"');
  expect(campus.html).toContain("M12 6l1.8 3.9");
  expect(captured.map(({ html }) => html).join("\n")).not.toMatch(/<script|onerror|<img/i);
});

test("shared_focus_uses_zoom_floor_and_ignores_null_position", async () => {
  const helpers = await requireMapUi();
  const calls: Array<[[number, number], number, { duration: number }]> = [];
  let zoom = 11;
  const map = {
    flyTo(position: [number, number], targetZoom: number, options: { duration: number }) {
      calls.push([position, targetZoom, options]);
    },
    getZoom() {
      return zoom;
    },
  };

  helpers.focusSelectedPosition(map, [10.01, 105.78]);
  zoom = 18;
  helpers.focusSelectedPosition(map, [10.02, 105.79]);
  helpers.focusSelectedPosition(map, null);

  expect(calls).toEqual([
    [[10.01, 105.78], 16, { duration: 0.6 }],
    [[10.02, 105.79], 18, { duration: 0.6 }],
  ]);
});

test("shared_resize_observer_invalidates_and_disconnects", async () => {
  const helpers = await requireMapUi();
  const previousDescriptor = Object.getOwnPropertyDescriptor(globalThis, "ResizeObserver");
  const resizeState: { callback: ResizeObserverCallback | null } = { callback: null };
  let observedContainer: Element | null = null;
  let disconnected = false;
  const container = {} as Element;

  class FakeResizeObserver {
    constructor(callback: ResizeObserverCallback) {
      resizeState.callback = callback;
    }

    observe(target: Element) {
      observedContainer = target;
    }

    disconnect() {
      disconnected = true;
    }
  }

  Object.defineProperty(globalThis, "ResizeObserver", {
    configurable: true,
    value: FakeResizeObserver,
  });

  try {
    let invalidations = 0;
    const cleanup = helpers.observeMapResize({
      getContainer: () => container,
      invalidateSize: () => {
        invalidations += 1;
      },
    });

    expect(observedContainer).toBe(container);
    const resizeCallback = resizeState.callback;
    if (resizeCallback === null) throw new Error("resize observer callback was not registered");
    resizeCallback([], {} as ResizeObserver);
    expect(invalidations).toBe(1);

    cleanup();
    expect(disconnected).toBe(true);
  } finally {
    if (previousDescriptor) {
      Object.defineProperty(globalThis, "ResizeObserver", previousDescriptor);
    } else {
      Reflect.deleteProperty(globalThis, "ResizeObserver");
    }
  }
});

test("shared_scroll_selects_only_the_requested_listing_and_ignores_null", async () => {
  const helpers = await requireMapUi();
  const selectors: string[] = [];
  const scrolls: Array<{ listingId: number; options: ScrollIntoViewOptions }> = [];
  const container = {
    querySelector(selector: string) {
      selectors.push(selector);
      if (selector !== '[data-listing-id="42"]') return null;
      return {
        scrollIntoView(options: ScrollIntoViewOptions) {
          scrolls.push({ listingId: 42, options });
        },
      };
    },
  } as unknown as HTMLElement;

  helpers.scrollMapSelection(container, 42);
  helpers.scrollMapSelection(container, 999);
  helpers.scrollMapSelection(container, null);

  expect(selectors).toEqual(['[data-listing-id="42"]', '[data-listing-id="999"]']);
  expect(scrolls).toEqual([
    { listingId: 42, options: { block: "nearest", behavior: "smooth" } },
  ]);
});
