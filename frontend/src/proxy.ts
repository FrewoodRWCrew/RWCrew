// This is Next.js's "proxy" file (called "middleware" in older Next.js
// versions): a small piece of code that runs on the server before a page
// is rendered. We use it to:
//   1. detect which language the visitor should see, and make sure every
//      URL has a language segment (e.g. redirecting bare "/" to "/nl"), and
//   2. silently renew an expired login (see refreshSessionOnServer).

import createIntlMiddleware from "next-intl/middleware";
import { NextRequest } from "next/server";
import { routing } from "./i18n/routing";
import {
  ACCESS_TOKEN_COOKIE_NAME,
  REFRESH_TOKEN_COOKIE_NAME,
  parseSetCookieNameValue,
  refreshSessionOnServer,
} from "./lib/session-refresh";

// Build the language-handling part from our language configuration.
const handleIntl = createIntlMiddleware(routing);

export default async function proxy(request: NextRequest) {
  // The browser drops the access cookie once its 15 minutes are up, while
  // the refresh cookie lives on for 30 days. That combination means "the
  // user is still logged in, they just need a new access token".
  const refreshToken = request.cookies.get(REFRESH_TOKEN_COOKIE_NAME)?.value;
  const needsRefresh = refreshToken !== undefined && !request.cookies.has(ACCESS_TOKEN_COOKIE_NAME);

  const refreshed = needsRefresh ? await refreshSessionOnServer(refreshToken) : null;

  if (refreshed) {
    // Put the new cookies on the incoming request too, so the Server
    // Components rendering THIS request already see the new session
    // (the intl handler below forwards the request's headers on).
    for (const setCookieHeader of refreshed.setCookieHeaders) {
      const { name, value } = parseSetCookieNameValue(setCookieHeader);
      request.cookies.set(name, value);
    }
  }

  const response = handleIntl(request);

  if (refreshed) {
    // ...and hand the same cookies to the browser so it keeps them. The
    // raw headers are forwarded untouched to keep the backend's cookie
    // settings (HttpOnly, SameSite, lifetime, path).
    for (const setCookieHeader of refreshed.setCookieHeaders) {
      response.headers.append("set-cookie", setCookieHeader);
    }
  }

  return response;
}

export const config = {
  // Run on every page, but skip API routes, Next.js's own internal
  // static/image files, and common static asset file extensions — none
  // of those need a language prefix.
  matcher: ["/((?!api|_next|.*\\..*).*)"],
};
