import { mobilityDisabled, proxyMobilityJson } from "@/lib/mobility-api";

export const dynamic = "force-dynamic";

export function GET(): Promise<Response> | Response {
  if (process.env.MOBILITY_ENABLED !== "true") return mobilityDisabled();
  return proxyMobilityJson("/mobility/campuses", { method: "GET" });
}
