// SERVER-side helper used by src/proxy.ts to keep a user logged in.
//
// The backend's access-token cookie only lives 15 minutes (see
// backend/app/core/config.py), after which the browser throws it away, while
// the refresh-token cookie lives until the 6-hour login session ends. When a page is requested with a
// refresh cookie but no access cookie, the proxy asks the backend for a
// fresh pair BEFORE the page renders, so the Server Components (which can't
// set cookies themselves) already see a valid session.
//
// Never import this from browser code — see refreshSessionInBrowser in
// api.ts for the client-side equivalent.

import { API_BASE_URL } from "./config";

export const ACCESS_TOKEN_COOKIE_NAME = "rwcrew_access_token";
export const REFRESH_TOKEN_COOKIE_NAME = "rwcrew_refresh_token";

/** The new cookies the backend issued, each as its raw "Set-Cookie" header value. */
export interface RefreshedSession {
  setCookieHeaders: string[];
}

// How long a finished refresh result is remembered, so requests that were
// already in flight carrying the SAME (now rotated-away) refresh token get
// the same new cookies instead of a 401 from the backend's rotation check.
// A browser fires several requests at once (page + link prefetches), so this
// is not a hypothetical race.
const RESULT_TTL_MS = 30_000;

// One entry per old refresh token: the pending or finished refresh call.
const recentRefreshes = new Map<string, { promise: Promise<RefreshedSession | null>; startedAt: number }>();

/**
 * Exchange a refresh token for a new access + refresh token pair.
 * Returns null when the backend refuses (expired/revoked token) or can't
 * be reached — the caller then just carries on and the normal
 * "not logged in" redirect takes over.
 */
export function refreshSessionOnServer(refreshToken: string): Promise<RefreshedSession | null> {
  const now = Date.now();

  // Forget old entries so this map can't grow forever.
  for (const [token, entry] of recentRefreshes) {
    if (now - entry.startedAt > RESULT_TTL_MS) recentRefreshes.delete(token);
  }

  // Someone already refreshed with this exact token: share their result.
  const existing = recentRefreshes.get(refreshToken);
  if (existing) return existing.promise;

  const promise = callBackendRefresh(refreshToken);
  recentRefreshes.set(refreshToken, { promise, startedAt: now });

  // A failed attempt shouldn't be remembered (the backend may just have
  // been briefly down), only successes need the sharing.
  void promise.then((result) => {
    if (result === null) recentRefreshes.delete(refreshToken);
  });

  return promise;
}

async function callBackendRefresh(refreshToken: string): Promise<RefreshedSession | null> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/auth/refresh`, {
      method: "POST",
      headers: { Cookie: `${REFRESH_TOKEN_COOKIE_NAME}=${refreshToken}` },
      cache: "no-store",
    });
    if (!response.ok) return null;

    const setCookieHeaders = response.headers.getSetCookie();
    return setCookieHeaders.length > 0 ? { setCookieHeaders } : null;
  } catch {
    // Backend unreachable: behave as if there was nothing to refresh.
    return null;
  }
}

/** Split "name=value; Path=/; ..." into just its name and value. */
export function parseSetCookieNameValue(setCookieHeader: string): { name: string; value: string } {
  const pair = setCookieHeader.split(";", 1)[0];
  const separatorIndex = pair.indexOf("=");
  return { name: pair.slice(0, separatorIndex).trim(), value: pair.slice(separatorIndex + 1).trim() };
}
