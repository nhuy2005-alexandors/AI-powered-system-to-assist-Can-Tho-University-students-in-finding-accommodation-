import type {
  Campus,
  CatalogListing,
  NearbyResult,
  Position,
  RouteResult,
} from "@/lib/mobility-contracts";

type Point = { lat: number; lng: number };

function project(point: Point, bounds: { south: number; north: number; west: number; east: number }) {
  const width = Math.max(bounds.east - bounds.west, 0.0001);
  const height = Math.max(bounds.north - bounds.south, 0.0001);
  const x = 70 + ((point.lng - bounds.west) / width) * 860;
  const y = 530 - ((point.lat - bounds.south) / height) * 460;
  return { x, y };
}

export default function OfflineCoordinateCanvas({
  listings,
  campuses,
  selectedListingId,
  routes,
  nearby,
}: {
  listings: CatalogListing[];
  campuses: Campus[];
  selectedListingId: number | null;
  routes: Partial<Record<Campus["id"], RouteResult>>;
  nearby: NearbyResult | null;
}) {
  const listingPoints = listings.flatMap((listing) =>
    listing.position ? [listing.position] : [],
  );
  const routePoints = Object.values(routes).flatMap((route) =>
    route?.status === "OK" &&
    route.evidence_kind === "SYNTHETIC_FIXTURE" &&
    route.polyline
      ? route.polyline
      : [],
  );
  const placePoints = nearby?.evidence_kind === "SYNTHETIC_FIXTURE"
    ? nearby.items
    : [];
  const allPoints: Point[] = [
    ...listingPoints,
    ...campuses,
    ...routePoints,
    ...placePoints,
  ];
  const bounds = allPoints.length
    ? {
        south: Math.min(...allPoints.map((point) => point.lat)) - 0.003,
        north: Math.max(...allPoints.map((point) => point.lat)) + 0.003,
        west: Math.min(...allPoints.map((point) => point.lng)) - 0.003,
        east: Math.max(...allPoints.map((point) => point.lng)) + 0.003,
      }
    : { south: 0, north: 1, west: 0, east: 1 };

  const liveGoogle =
    Object.values(routes).some(
      (route) => route?.provider.toLowerCase() === "google" && route.evidence_kind === "LIVE",
    ) ||
    (nearby?.provider.toLowerCase() === "google" && nearby.evidence_kind === "LIVE");

  return (
    <div className="rounded-xl border border-slate-200 bg-white shadow-sm">
      <div className="flex flex-wrap items-start justify-between gap-3 border-b border-slate-100 px-4 py-3">
        <div>
          <h2 className="font-semibold text-slate-900">Sơ đồ tọa độ tạm thời</h2>
          <p className="mt-1 text-xs text-slate-600">
            Vị trí có thể gần đúng; lối vào khuôn viên chưa được xác minh.
          </p>
        </div>
        <p className="rounded-full bg-amber-50 px-3 py-1 text-xs font-medium text-amber-900">
          Google Maps chưa được cấu hình
        </p>
      </div>
      {liveGoogle && (
        <p data-testid="live-google-hidden" className="px-4 pt-3 text-sm text-amber-900">
          Dữ liệu Google trực tiếp chưa được vẽ trên sơ đồ offline này.
        </p>
      )}
      <svg
        data-testid="offline-map"
        data-renderer="synthetic-coordinate-canvas"
        className="h-[320px] w-full"
        viewBox="0 0 1000 600"
        role="img"
        aria-label="Sơ đồ tọa độ tạm thời, không phải bản đồ nền"
      >
        <defs>
          <pattern id="mobility-grid" width="50" height="50" patternUnits="userSpaceOnUse">
            <path d="M 50 0 L 0 0 0 50" fill="none" stroke="#e2e8f0" strokeWidth="1" />
          </pattern>
        </defs>
        <rect x="0" y="0" width="1000" height="600" fill="url(#mobility-grid)" />
        <text x="28" y="38" fill="#64748b" fontSize="17">
          Sơ đồ theo tọa độ · chưa xác minh lối vào
        </text>

        {Object.values(routes).map((route) => {
          if (
            route?.status !== "OK" ||
            route.evidence_kind !== "SYNTHETIC_FIXTURE" ||
            !route.polyline
          ) {
            return null;
          }
          const points = route.polyline.map((point) => project(point, bounds));
          return (
            <polyline
              key={`route-${route.campus_id}`}
              data-route-source={route.evidence_kind}
              points={points.map((point) => `${point.x},${point.y}`).join(" ")}
              fill="none"
              stroke="#7c3aed"
              strokeWidth="5"
              strokeDasharray="12 8"
            />
          );
        })}

        {placePoints.map((place) => {
          const point = project(place, bounds);
          return (
            <g key={place.provider_place_id} data-nearby-place-id={place.provider_place_id}>
              <circle cx={point.x} cy={point.y} r="9" fill="#d97706" stroke="white" strokeWidth="3" />
            </g>
          );
        })}

        {listings.map((listing) => {
          if (!listing.position) return null;
          const point = project(listing.position, bounds);
          const selected = listing.id === selectedListingId;
          return (
            <g
              key={listing.id}
              data-listing-pin-id={listing.id}
              data-precision={listing.position.precision}
            >
              <circle
                cx={point.x}
                cy={point.y}
                r={selected ? 11 : 5}
                fill={selected ? "#047857" : "#e11d48"}
                stroke="white"
                strokeWidth="2"
              />
            </g>
          );
        })}

        {campuses.map((campus) => {
          const point = project(campus, bounds);
          return (
            <g
              key={campus.id}
              data-campus-id={campus.id}
              data-lat={campus.lat}
              data-lng={campus.lng}
              data-verification={campus.verification_status}
            >
              <rect x={point.x - 7} y={point.y - 7} width="14" height="14" rx="3" fill="#1d4ed8" />
              <text x={point.x + 12} y={point.y + 5} fill="#1e3a8a" fontSize="13">
                {campus.name}
              </text>
            </g>
          );
        })}
      </svg>
      <div className="flex flex-wrap gap-x-5 gap-y-1 border-t border-slate-100 px-4 py-2 text-xs text-slate-600">
        <span><span className="mr-1 inline-block h-2.5 w-2.5 rounded-full bg-rose-600" />Tin có tọa độ</span>
        <span><span className="mr-1 inline-block h-2.5 w-2.5 rounded-sm bg-blue-700" />Khuôn viên</span>
        <span>Tin thiếu tọa độ không có ghim</span>
      </div>
    </div>
  );
}
