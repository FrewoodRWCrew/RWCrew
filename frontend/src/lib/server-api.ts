// A small helper for SERVER components/pages that need to fetch data
// (modules, admin lists, ...) straight from the backend during
// rendering, so pages show real data immediately instead of a loading
// spinner that then pops in client-side data a moment later.
//
// It works the same way as getCurrentUserOnServer in server-auth.ts:
// forward the incoming request's cookies to the backend, so the backend
// recognises the same logged-in session.

import { cookies } from "next/headers";
import { API_BASE_URL } from "./config";

export class ServerApiError extends Error {
  constructor(
    message: string,
    public readonly status: number,
  ) {
    super(message);
    this.name = "ServerApiError";
  }
}

export async function serverApiFetch<TResponse>(path: string): Promise<TResponse> {
  const cookieStore = await cookies();

  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: { Cookie: cookieStore.toString() },
    // Data like module access can change at any time from the admin
    // screen, so we always ask the backend fresh rather than caching.
    cache: "no-store",
  });

  if (!response.ok) {
    const errorBody = await response.json().catch(() => null);
    const message = errorBody?.detail ?? `Request failed with status ${response.status}`;
    throw new ServerApiError(message, response.status);
  }

  return (await response.json()) as TResponse;
}
