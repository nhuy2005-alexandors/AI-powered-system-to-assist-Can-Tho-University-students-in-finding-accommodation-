// v1 boundary shared with app/mobility/contracts.py. Units remain seconds/meters.
export type TravelMode = "MOTORBIKE" | "WALK" | "BICYCLE" | "BUS";
export type CampusId = "khu_i" | "khu_ii" | "khu_iii";
export type PlaceCategory = "grocery" | "market" | "pharmacy" | "healthcare" | "police" | "bus_stop";
export type EvidenceKind = "NONE" | "SYNTHETIC_FIXTURE" | "LIVE";
export type Precision = "APPROXIMATE" | "VERIFIED" | "UNKNOWN";
export type Position = { lat: number; lng: number; precision: Precision; source: string | null; verified_at: string | null };
export type Campus = { id: CampusId; name: string; lat: number; lng: number; coordinate_version: string; verification_status: "PROVISIONAL" | "VERIFIED" };
export type CatalogListing = {
  id: number; title: string; source: string; source_id: string;
  source_url: string | null; source_contact_url: string | null;
  price: number | null; area: number | null; address: string | null; district: string | null;
  description: string | null; images: string[];
  housing_type: string | null; offer_kind: string | null;
  description_state: string | null; description_completeness: string | null;
  description_is_partial: boolean | null; unit_type_uncertain: boolean | null;
  offer_context_uncertain: boolean | null; mixed_use_possible: boolean | null;
  lease_transfer_terms_verified: boolean | null;
  parsed_amenities: Record<string, boolean | null> | null;
  position: Position | null;
};
export type CatalogPage = { items: CatalogListing[]; total: number; page: number; size: number };
export type RouteRequest = {
  listing_id: number; campus_id: CampusId; requested_mode: TravelMode;
  departure_time?: string | null; direction?: "LISTING_TO_CAMPUS";
};
export type RouteStatus = "NOT_CONFIGURED" | "CAPABILITY_UNVERIFIED" | "UNSUPPORTED_MODE" |
  "LOCATION_UNAVAILABLE" | "NO_ROUTE" | "RATE_LIMITED" | "PROVIDER_ERROR" | "OK";
export type LocationWarning = {
  code: string; severity: "INFO" | "CAUTION"; message: string; evidence_source: string;
  scope: string; observed_at: string | null;
};
export type RouteResult = {
  listing_id: number; campus_id: CampusId; provider: string;
  attribution: string[]; provider_profile: string | null; requested_mode: TravelMode;
  effective_mode: TravelMode | null; direction: "LISTING_TO_CAMPUS"; status: RouteStatus;
  duration_seconds: number | null; distance_meters: number | null; polyline: Position[] | null;
  observed_at: string | null; coordinate_version: string; evidence_kind: EvidenceKind;
  warnings: LocationWarning[];
};
export type NearbyRequest = { listing_id: number; radius_m?: 500 | 1000 | 2000; categories?: PlaceCategory[] };
export type NearbyStatus = "NOT_CONFIGURED" | "CAPABILITY_UNVERIFIED" | "UNSUPPORTED_CATEGORY" |
  "LOCATION_UNAVAILABLE" | "EMPTY" | "RATE_LIMITED" | "PROVIDER_ERROR" | "OK";
export type Place = {
  provider_place_id: string; name: string; category: PlaceCategory; lat: number; lng: number;
  straight_line_distance_m: number | null; attribution: string[];
};
export type NearbyResult = {
  listing_id: number; radius_m: 500 | 1000 | 2000; categories: PlaceCategory[]; provider: string;
  status: NearbyStatus; evidence_kind: EvidenceKind; items: Place[]; queried_at: string | null;
  center_precision: Precision; coverage: "UNKNOWN" | "PARTIAL"; truncated: boolean;
};
