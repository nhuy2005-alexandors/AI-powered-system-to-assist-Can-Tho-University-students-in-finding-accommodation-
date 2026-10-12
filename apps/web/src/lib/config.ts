// Server-side config. API_INTERNAL_URL dùng cho fetch trong docker network
// (browser không chạm được `api:8000`); fallback localhost khi chạy ngoài docker.
export const API_URL =
  process.env.API_INTERNAL_URL ?? process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export type MobilityMapConfig = {
  enabled: boolean;
  tileUrl: string | null;
  allowedTileOrigin: string | null;
  attribution: string;
};

const DISABLED_MAP_CONFIG: MobilityMapConfig = {
  enabled: false,
  tileUrl: null,
  allowedTileOrigin: null,
  attribution: "",
};

export function mobilityMapConfig(): MobilityMapConfig {
  if (
    process.env.MOBILITY_ENABLED !== "true" ||
    process.env.MOBILITY_TILES_ENABLED !== "true"
  ) {
    return DISABLED_MAP_CONFIG;
  }

  const configuredUrl = process.env.MOBILITY_TILE_URL?.trim() ?? "";
  const configuredOrigin = process.env.MOBILITY_ALLOWED_TILE_ORIGIN?.trim() ?? "";
  const attribution = process.env.MOBILITY_TILE_ATTRIBUTION?.trim() ?? "";
  if (!configuredUrl || !configuredOrigin || !attribution) return DISABLED_MAP_CONFIG;

  try {
    const tile = new URL(configuredUrl);
    const allowedOrigin = new URL(configuredOrigin);
    if (
      tile.protocol !== "https:" ||
      allowedOrigin.protocol !== "https:" ||
      tile.username ||
      tile.password ||
      tile.search ||
      tile.hash ||
      tile.origin !== allowedOrigin.origin ||
      (allowedOrigin.pathname !== "/" && allowedOrigin.pathname !== "") ||
      allowedOrigin.username ||
      allowedOrigin.password ||
      allowedOrigin.search ||
      allowedOrigin.hash
    ) {
      return DISABLED_MAP_CONFIG;
    }
    return {
      enabled: true,
      // Keep Leaflet's {z}/{x}/{y} template intact after URL validation.
      tileUrl: configuredUrl,
      allowedTileOrigin: allowedOrigin.origin,
      attribution,
    };
  } catch {
    return DISABLED_MAP_CONFIG;
  }
}

export const ACCESS_COOKIE = "access_token";
export const REFRESH_COOKIE = "refresh_token";

// TTL khớp backend (config.py: access 15min, refresh 30 ngày).
export const ACCESS_MAX_AGE = 15 * 60;
export const REFRESH_MAX_AGE = 30 * 24 * 60 * 60;
