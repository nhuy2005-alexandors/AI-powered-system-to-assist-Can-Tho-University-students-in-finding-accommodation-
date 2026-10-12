import { refresh, type ApiError, type TokenPair } from "./api";
import {
  clearAuthCookies,
  getAccessToken,
  getRefreshToken,
  setAuthCookies,
} from "./session";

type AuthenticatedOperation<T> = (accessToken: string) => Promise<T>;

// Coalesce refreshes that arrive concurrently in the same Next.js process. The
// backend rotates refresh tokens, so sending the same token twice would revoke
// the first request's replacement session.
const refreshFlights = new Map<string, Promise<TokenPair>>();

function unauthorized(detail = "Phiên đăng nhập đã hết hạn"): ApiError {
  return { status: 401, detail };
}

function isUnauthorized(error: unknown): boolean {
  return (error as Partial<ApiError> | null)?.status === 401;
}

function rotate(refreshToken: string): Promise<TokenPair> {
  const running = refreshFlights.get(refreshToken);
  if (running) return running;

  const request = refresh(refreshToken).finally(() => {
    refreshFlights.delete(refreshToken);
  });
  refreshFlights.set(refreshToken, request);
  return request;
}

/**
 * Run an API operation with the cookie-backed access token. If the token is
 * absent or rejected, rotate the refresh token once, update both cookies and
 * retry. Only call this from Route Handlers/Server Actions, where cookies may
 * be mutated.
 */
export async function withAccessToken<T>(
  operation: AuthenticatedOperation<T>,
): Promise<T> {
  const accessToken = getAccessToken();
  const refreshToken = getRefreshToken();

  if (accessToken) {
    try {
      return await operation(accessToken);
    } catch (error) {
      if (!isUnauthorized(error)) throw error;
    }
  }

  if (!refreshToken) {
    clearAuthCookies();
    throw unauthorized(accessToken ? undefined : "Chưa đăng nhập");
  }

  let tokens: TokenPair;
  try {
    tokens = await rotate(refreshToken);
  } catch {
    clearAuthCookies();
    throw unauthorized();
  }

  setAuthCookies(tokens.access_token, tokens.refresh_token);
  try {
    return await operation(tokens.access_token);
  } catch (error) {
    if (isUnauthorized(error)) clearAuthCookies();
    throw error;
  }
}
