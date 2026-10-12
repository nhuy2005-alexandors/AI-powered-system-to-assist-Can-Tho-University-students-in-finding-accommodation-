import {
  invalidMobilityRequest,
  mobilityDisabled,
  proxyMobilityJson,
  readAllowedMobilityJson,
} from "@/lib/mobility-api";

export const dynamic = "force-dynamic";

const ALLOWED_FIELDS = [
  "listing_id",
  "campus_id",
  "requested_mode",
  "departure_time",
  "direction",
] as const;

export async function POST(request: Request): Promise<Response> {
  if (process.env.MOBILITY_ENABLED !== "true") return mobilityDisabled();
  const body = await readAllowedMobilityJson(request, ALLOWED_FIELDS);
  if (!body) return invalidMobilityRequest();
  return proxyMobilityJson("/mobility/routes", { method: "POST", body });
}
