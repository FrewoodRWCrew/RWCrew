// This helper is used by SERVER components/layouts only (never in the
// browser) to find out who is logged in, by reading the same auth
// cookies the browser would send, and asking the backend to confirm
// them. Doing this on the server (instead of only in the browser) means
// a protected page never briefly "flashes" its content before redirecting
// an unauthenticated visitor away.

import { cookies } from "next/headers";
import { API_BASE_URL } from "./config";
import type { CurrentUser } from "./types";

/**
 * Look up the currently logged-in user for this request, or return null
 * if nobody is logged in (or their session has expired).
 */
export async function getCurrentUserOnServer(): Promise<CurrentUser | null> {
  // Next.js's cookies() function is asynchronous in this Next.js version.
  const cookieStore = await cookies();

  const response = await fetch(`${API_BASE_URL}/api/auth/me`, {
    // Forward every cookie the browser sent us along to the backend, so
    // it can recognise the same login session.
    headers: { Cookie: cookieStore.toString() },
    // Never cache this request: whether someone is logged in can change
    // at any moment (e.g. after logging out in another tab).
    cache: "no-store",
  });

  if (!response.ok) {
    return null;
  }

  return (await response.json()) as CurrentUser;
}
