import {
  invalidMobilityRequest,
  mobilityDisabled,
  proxyMobilityJson,
} from "@/lib/mobility-api";

export const dynamic = "force-dynamic";

const ALLOWED_QUERY = new Set(["page", "size", "south", "north", "west", "east"]);

export function GET(request: Request): Promise<Response> | Response {
  if (process.env.MOBILITY_ENABLED !== "true") return mobilityDisabled();

  const incoming = new URL(request.url);
  if ([...incoming.searchParams.keys()].some((key) => !ALLOWED_QUERY.has(key))) {
    return invalidMobilityRequest();
  }
  const query = new URLSearchParams();
  for (const key of ALLOWED_QUERY) {
    const value = incoming.searchParams.get(key);
    if (value !== null) query.set(key, value);
  }
  const suffix = query.size > 0 ? `?${query.toString()}` : "";
  return proxyMobilityJson(`/mobility/listings${suffix}`, { method: "GET" });
}
