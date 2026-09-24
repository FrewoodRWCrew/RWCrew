// The app's only door to the backend. Everything the phone knows about the
// server goes through here: login, silent token refresh and the version
// header. Tokens live in the phone's secure storage (Keychain on iOS,
// Keystore on Android), never in plain storage.

import * as SecureStore from "expo-secure-store";

import { API_URL, APP_VERSION } from "./config";
import type { CurrentUser } from "./types";

const ACCESS_KEY = "rwcrew_access_token";
const REFRESH_KEY = "rwcrew_refresh_token";

export type { CurrentUser };

// What login/refresh return (mirrors the contract's MobileTokenResponse).
type TokenResponse = {
  access_token: string;
  refresh_token: string;
  expires_in: number;
  user: CurrentUser;
};

// An error carrying the HTTP status, so screens can react (e.g. 426 = update the app).
export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

// Read the "detail" text FastAPI puts in error responses, if there is one.
async function errorMessage(response: Response): Promise<string> {
  try {
    const body = await response.json();
    // Most errors carry a plain text detail...
    if (typeof body?.detail === "string") return body.detail;
    // ...validation errors (422) carry a list of problems instead.
    if (Array.isArray(body?.detail)) {
      return body.detail.map((problem: { msg?: string }) => problem.msg ?? "").filter(Boolean).join(", ");
    }
  } catch {
    // Not JSON: fall through to the generic message.
  }
  return `Request failed (${response.status})`;
}

// Turn a failed response into an ApiError (used by module-api.ts too).
export async function apiErrorFrom(response: Response): Promise<ApiError> {
  return new ApiError(response.status, await errorMessage(response));
}

// Plain request to the backend, always announcing our version.
async function rawRequest(path: string, init: RequestInit = {}, accessToken?: string): Promise<Response> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    "X-App-Version": APP_VERSION,
    ...(init.headers as Record<string, string> | undefined),
  };
  if (accessToken) headers.Authorization = `Bearer ${accessToken}`;
  return fetch(`${API_URL}${path}`, { ...init, headers });
}

// Save a fresh token pair to secure storage.
async function storeTokens(tokens: TokenResponse): Promise<void> {
  await SecureStore.setItemAsync(ACCESS_KEY, tokens.access_token);
  await SecureStore.setItemAsync(REFRESH_KEY, tokens.refresh_token);
}

// Forget both tokens (logout, or a session that can no longer be refreshed).
export async function clearTokens(): Promise<void> {
  await SecureStore.deleteItemAsync(ACCESS_KEY);
  await SecureStore.deleteItemAsync(REFRESH_KEY);
}

export async function hasStoredSession(): Promise<boolean> {
  return (await SecureStore.getItemAsync(REFRESH_KEY)) !== null;
}

// The backend rotates the refresh token on every use, so two refreshes at
// once with the same token would make the second one fail. Share ONE
// in-flight refresh between all callers.
let refreshInFlight: Promise<boolean> | null = null;

async function refreshSession(): Promise<boolean> {
  if (refreshInFlight === null) {
    refreshInFlight = (async () => {
      const refreshToken = await SecureStore.getItemAsync(REFRESH_KEY);
      if (refreshToken === null) return false;
      const response = await rawRequest("/api/mobile/v1/auth/refresh", {
        method: "POST",
        body: JSON.stringify({ refresh_token: refreshToken }),
      });
      if (!response.ok) return false;
      await storeTokens((await response.json()) as TokenResponse);
      return true;
    })().finally(() => {
      refreshInFlight = null;
    });
  }
  return refreshInFlight;
}

// Call a protected endpoint with the stored access token. On a 401 it
// refreshes the session once and retries, so users stay logged in silently.
export async function authedFetch(path: string, init: RequestInit = {}): Promise<Response> {
  const send = async () => rawRequest(path, init, (await SecureStore.getItemAsync(ACCESS_KEY)) ?? undefined);

  let response = await send();
  if (response.status === 401 && (await refreshSession())) {
    response = await send();
  }
  return response;
}

// Log in with email + password; on success the tokens are stored.
export async function login(email: string, password: string): Promise<CurrentUser> {
  const response = await rawRequest("/api/mobile/v1/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
  if (!response.ok) throw new ApiError(response.status, await errorMessage(response));
  const tokens = (await response.json()) as TokenResponse;
  await storeTokens(tokens);
  return tokens.user;
}

// Ask the backend who we are (null when there is no valid session).
export async function fetchCurrentUser(): Promise<CurrentUser | null> {
  const response = await authedFetch("/api/mobile/v1/auth/me");
  if (response.status === 401) {
    await clearTokens();
    return null;
  }
  if (!response.ok) throw new ApiError(response.status, await errorMessage(response));
  return (await response.json()) as CurrentUser;
}

// Log out: revoke the refresh token on the server (best effort), then forget the tokens locally.
export async function logout(): Promise<void> {
  const refreshToken = await SecureStore.getItemAsync(REFRESH_KEY);
  if (refreshToken !== null) {
    try {
      await rawRequest("/api/mobile/v1/auth/logout", {
        method: "POST",
        body: JSON.stringify({ refresh_token: refreshToken }),
      });
    } catch {
      // Offline: we still log out locally below.
    }
  }
  await clearTokens();
}
