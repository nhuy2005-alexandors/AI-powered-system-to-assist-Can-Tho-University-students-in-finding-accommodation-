import type { Page } from "@playwright/test";
import type {
  Campus,
  CatalogListing,
  CatalogPage,
  NearbyRequest,
  NearbyResult,
  PlaceCategory,
  Position,
  RouteRequest,
  RouteResult,
} from "../src/lib/mobility-contracts";

export type FixtureReply = { status: number; body: unknown };
export type CapturedMobilityRequest = {
  method: string;
  path: string;
  query: Record<string, string>;
  body?: unknown;
};

type Deferred<T> = {
  promise: Promise<T>;
  resolve: (value: T) => void;
};

function deferred<T>(): Deferred<T> {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((done) => {
    resolve = done;
  });
  return { promise, resolve };
}

type Hold<T> = {
  matches: (body: T) => boolean;
  matched: boolean;
  seen: Deferred<T>;
  reply: Deferred<FixtureReply>;
  settled: Deferred<void>;
};

export type HeldRequest<T> = {
  seen: Promise<T>;
  settled: Promise<void>;
  release: (reply: FixtureReply) => void;
};

function createHold<T>(matches: (body: T) => boolean): {
  hold: Hold<T>;
  request: HeldRequest<T>;
} {
  const hold: Hold<T> = {
    matches,
    matched: false,
    seen: deferred<T>(),
    reply: deferred<FixtureReply>(),
    settled: deferred<void>(),
  };
  return {
    hold,
    request: {
      seen: hold.seen.promise,
      settled: hold.settled.promise,
      release: (reply) => hold.reply.resolve(reply),
    },
  };
}

export function syntheticCampuses(): Campus[] {
  return [
    {
      id: "khu_i",
      name: "Khu I · fixture",
      lat: 10.11,
      lng: 105.11,
      coordinate_version: "SYNTHETIC_FIXTURE_v1",
      verification_status: "PROVISIONAL",
    },
    {
      id: "khu_ii",
      name: "Khu II · fixture",
      lat: 10.22,
      lng: 105.22,
      coordinate_version: "SYNTHETIC_FIXTURE_v1",
      verification_status: "PROVISIONAL",
    },
    {
      id: "khu_iii",
      name: "Khu III · fixture",
      lat: 10.33,
      lng: 105.33,
      coordinate_version: "SYNTHETIC_FIXTURE_v1",
      verification_status: "PROVISIONAL",
    },
  ];
}

export function syntheticListing(index: number, total: number): CatalogListing {
  const missingPosition = total === 789 && index >= 788;
  let position: Position | null = null;
  if (!missingPosition) {
    position = {
      lat: 10.1 + (index % 40) * 0.0002,
      lng: 105.1 + Math.floor(index / 40) * 0.0002,
      precision: "APPROXIMATE",
      source: "SYNTHETIC_FIXTURE",
      verified_at: null,
    };
  }

  const first = index === 1;
  const second = index === 2;
  return {
    id: 900_000 + index,
    title: first ? "Tin fixture thiếu diện tích" : `Tin fixture ${index}`,
    source: "SYNTHETIC_FIXTURE",
    source_id: `fixture-${index}`,
    source_url: `https://source.example.test/listing/${index}`,
    source_contact_url: first
      ? "javascript:alert('unsafe')"
      : second
        ? `https://contact.example.test/listing/${index}`
        : null,
    price: 2_500_000 + index,
    area: first ? null : 20 + (index % 10),
    address: `Địa chỉ fixture ${index}`,
    district: "Quận fixture",
    description: first
      ? "<script>window.__fixtureInjected=true</script> Nội dung tổng hợp, chưa đầy đủ."
      : `Mô tả fixture ${index}`,
    images: [],
    housing_type: first ? null : "ROOM",
    offer_kind: first ? "lease_transfer" : "RENT",
    description_state: first ? "PARTIAL" : "COMPLETE",
    description_completeness: first ? "PARTIAL" : "COMPLETE",
    description_is_partial: first,
    unit_type_uncertain: first ? null : false,
    offer_context_uncertain: first,
    mixed_use_possible: first,
    lease_transfer_terms_verified: first ? false : true,
    parsed_amenities: { air_conditioning: null, parking: true },
    position,
  };
}

export function syntheticCatalogPage(
  page: number,
  size: number,
  total: number,
): CatalogPage {
  const first = (page - 1) * size + 1;
  const last = Math.min(first + size - 1, total);
  const items = first <= total
    ? Array.from({ length: last - first + 1 }, (_, offset) =>
        syntheticListing(first + offset, total),
      )
    : [];
  return { items, total, page, size };
}

function fixturePosition(lat: number, lng: number): Position {
  return {
    lat,
    lng,
    precision: "APPROXIMATE",
    source: "SYNTHETIC_FIXTURE",
    verified_at: null,
  };
}

export function syntheticRouteResult(
  request: RouteRequest,
  options: { status?: RouteResult["status"]; warning?: boolean } = {},
): RouteResult {
  const status = options.status ?? "OK";
  const successful = status === "OK";
  return {
    listing_id: request.listing_id,
    campus_id: request.campus_id,
    provider: "google",
    attribution: [],
    provider_profile: null,
    requested_mode: request.requested_mode,
    effective_mode: successful ? request.requested_mode : null,
    direction: "LISTING_TO_CAMPUS",
    status,
    duration_seconds: successful
      ? request.requested_mode === "BUS" ? 120 : 60
      : null,
    distance_meters: successful ? 2_450 : null,
    polyline: successful
      ? [fixturePosition(10.101, 105.101), fixturePosition(10.11, 105.11)]
      : null,
    observed_at: successful ? "2030-04-05T02:30:00Z" : null,
    coordinate_version: "SYNTHETIC_FIXTURE_v1",
    evidence_kind: successful ? "SYNTHETIC_FIXTURE" : "NONE",
    warnings: options.warning
      ? [
          {
            code: "GOOGLE_ROUTE_BETA",
            severity: "CAUTION",
            message:
              "Tuyến đi bộ, xe đạp và xe máy của Google đang ở giai đoạn beta.",
            evidence_source: "SYNTHETIC_FIXTURE",
            scope: "route",
            observed_at: null,
          },
        ]
      : [],
  };
}

export function syntheticNearbyResult(
  request: NearbyRequest,
  options: { status?: NearbyResult["status"]; categories?: PlaceCategory[] } = {},
): NearbyResult {
  const status = options.status ?? "OK";
  const categories = options.categories ?? request.categories ?? [
    "grocery",
    "market",
    "pharmacy",
    "healthcare",
    "police",
    "bus_stop",
  ];
  const successful = status === "OK" || status === "EMPTY";
  const items = status === "OK"
    ? [
        {
          provider_place_id: "fixture-place-1",
          name: "Tiện ích tổng hợp fixture",
          category: categories[0] ?? "grocery",
          lat: 10.1015,
          lng: 105.1015,
          straight_line_distance_m: 175,
          attribution: ["SYNTHETIC_FIXTURE"],
        },
      ]
    : [];
  return {
    listing_id: request.listing_id,
    radius_m: request.radius_m ?? 1000,
    categories,
    provider: "google",
    status,
    evidence_kind: successful ? "SYNTHETIC_FIXTURE" : "NONE",
    items,
    queried_at: successful ? "2030-04-05T02:30:00Z" : null,
    center_precision: successful ? "APPROXIMATE" : "UNKNOWN",
    coverage: successful ? "PARTIAL" : "UNKNOWN",
    truncated: false,
  };
}

export type MobilityTransport = {
  externalAttempts: string[];
  requests: CapturedMobilityRequest[];
  setCatalogTotal(total: number): void;
  setRouteResponder(responder: (request: RouteRequest) => FixtureReply): void;
  setNearbyResponder(responder: (request: NearbyRequest) => FixtureReply): void;
  holdNextRoute(matches: (request: RouteRequest) => boolean): HeldRequest<RouteRequest>;
  holdNextNearby(matches: (request: NearbyRequest) => boolean): HeldRequest<NearbyRequest>;
};

function makeHold<T>(matches: (body: T) => boolean): {
  hold: Hold<T>;
  request: HeldRequest<T>;
} {
  return createHold(matches);
}

export async function installMobilityTransport(page: Page): Promise<MobilityTransport> {
  const externalAttempts: string[] = [];
  const requests: CapturedMobilityRequest[] = [];
  const routeHolds: Hold<RouteRequest>[] = [];
  const nearbyHolds: Hold<NearbyRequest>[] = [];
  let catalogTotal = 3;
  let routeResponder = (body: RouteRequest): FixtureReply => ({
    status: 200,
    body: syntheticRouteResult(body, { status: "NOT_CONFIGURED" }),
  });
  let nearbyResponder = (body: NearbyRequest): FixtureReply => ({
    status: 200,
    body: syntheticNearbyResult(body, { status: "NOT_CONFIGURED" }),
  });
  const campusOrigin = "http://localhost:3031";

  await page.route("**/*", async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    if (url.origin !== campusOrigin) {
      externalAttempts.push(`${request.method()} ${request.url()}`);
      await route.abort();
      return;
    }

    if (url.pathname === "/api/mobility/campuses" && request.method() === "GET") {
      requests.push({ method: "GET", path: url.pathname, query: {} });
      await route.fulfill({ status: 200, json: syntheticCampuses() });
      return;
    }

    if (url.pathname === "/api/mobility/listings" && request.method() === "GET") {
      const pageNumber = Number(url.searchParams.get("page") ?? "1");
      const size = Number(url.searchParams.get("size") ?? "50");
      requests.push({
        method: "GET",
        path: url.pathname,
        query: Object.fromEntries(url.searchParams.entries()),
      });
      await route.fulfill({
        status: 200,
        json: syntheticCatalogPage(pageNumber, size, catalogTotal),
      });
      return;
    }

    if (url.pathname === "/api/mobility/routes" && request.method() === "POST") {
      const body = (request.postDataJSON() ?? {}) as RouteRequest;
      requests.push({ method: "POST", path: url.pathname, query: {}, body });
      const held = routeHolds.find((candidate) =>
        !candidate.matched && candidate.matches(body),
      );
      if (held) {
        held.matched = true;
        held.seen.resolve(body);
        const reply = await held.reply.promise;
        try {
          await route.fulfill({ status: reply.status, json: reply.body });
        } catch {
          // The browser may already have cancelled the request; completion still wakes the test.
        } finally {
          held.settled.resolve();
        }
        return;
      }
      const reply = routeResponder(body);
      await route.fulfill({ status: reply.status, json: reply.body });
      return;
    }

    if (url.pathname === "/api/mobility/nearby" && request.method() === "POST") {
      const body = (request.postDataJSON() ?? {}) as NearbyRequest;
      requests.push({ method: "POST", path: url.pathname, query: {}, body });
      const held = nearbyHolds.find((candidate) =>
        !candidate.matched && candidate.matches(body),
      );
      if (held) {
        held.matched = true;
        held.seen.resolve(body);
        const reply = await held.reply.promise;
        try {
          await route.fulfill({ status: reply.status, json: reply.body });
        } catch {
          // The browser may already have cancelled the request; completion still wakes the test.
        } finally {
          held.settled.resolve();
        }
        return;
      }
      const reply = nearbyResponder(body);
      await route.fulfill({ status: reply.status, json: reply.body });
      return;
    }

    await route.continue();
  });

  return {
    externalAttempts,
    requests,
    setCatalogTotal: (total) => {
      catalogTotal = total;
    },
    setRouteResponder: (responder) => {
      routeResponder = responder;
    },
    setNearbyResponder: (responder) => {
      nearbyResponder = responder;
    },
    holdNextRoute: (matches) => {
      const created = makeHold(matches);
      routeHolds.push(created.hold);
      return created.request;
    },
    holdNextNearby: (matches) => {
      const created = makeHold(matches);
      nearbyHolds.push(created.hold);
      return created.request;
    },
  };
}
