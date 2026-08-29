// This file is the ONE place in the frontend that knows how to talk to
// our FastAPI backend from the browser. Every component that needs data
// (logging in, listing modules, managing access, ...) calls a function
// from here, instead of calling "fetch" directly all over the codebase.

import { API_BASE_URL } from "./config";
import type {
  CurrentUser,
  ModuleInfo,
  ModuleRoleAssignment,
  ModuleRoleName,
  ModuleStatus,
  Season,
  UserSummary,
} from "./types";

/** Thrown whenever the backend responds with an error status code. */
export class ApiError extends Error {
  constructor(
    message: string,
    // The HTTP status code the backend responded with (e.g. 401, 403).
    public readonly status: number,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

/**
 * Send one request to the backend and return its parsed JSON response.
 *
 * "credentials: include" is essential here: it tells the browser to
 * attach our login cookies to the request, and to store any new cookies
 * the backend sends back (e.g. right after logging in).
 */
async function apiFetch<TResponse>(path: string, init?: RequestInit): Promise<TResponse> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...init?.headers,
    },
  });

  if (!response.ok) {
    // Try to read the backend's own error message (FastAPI sends
    // {"detail": "..."}), falling back to a generic one if that fails.
    const errorBody = await response.json().catch(() => null);
    const message = errorBody?.detail ?? `Request failed with status ${response.status}`;
    throw new ApiError(message, response.status);
  }

  // A 204 "No Content" response has no JSON body to parse.
  if (response.status === 204) {
    return undefined as TResponse;
  }

  return (await response.json()) as TResponse;
}

// --- Authentication -------------------------------------------------

export function login(email: string, password: string): Promise<CurrentUser> {
  return apiFetch<CurrentUser>("/api/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
}

export function logout(): Promise<{ logged_out: boolean }> {
  return apiFetch("/api/auth/logout", { method: "POST" });
}

export function getCurrentUser(): Promise<CurrentUser> {
  return apiFetch<CurrentUser>("/api/auth/me");
}

// --- Modules (visible to any logged-in user) -------------------------

export function listModules(): Promise<ModuleInfo[]> {
  return apiFetch<ModuleInfo[]>("/api/modules");
}

export function getModuleStatus(moduleKey: string): Promise<ModuleStatus> {
  return apiFetch<ModuleStatus>(`/api/modules/${moduleKey}/status`);
}

export function listModuleRoles(moduleKey: string): Promise<ModuleRoleAssignment[]> {
  return apiFetch<ModuleRoleAssignment[]>(`/api/modules/${moduleKey}/roles`);
}

export function setModuleRole(
  moduleKey: string,
  userId: number,
  role: ModuleRoleName | null,
): Promise<ModuleRoleAssignment> {
  return apiFetch<ModuleRoleAssignment>(`/api/modules/${moduleKey}/roles/${userId}`, {
    method: "PUT",
    body: JSON.stringify({ role }),
  });
}

// --- Super-admin-only endpoints ---------------------------------------

export function listAdminUsers(): Promise<UserSummary[]> {
  return apiFetch<UserSummary[]>("/api/admin/users");
}

export function createUser(payload: {
  email: string;
  password: string;
  display_name: string;
  is_super_admin: boolean;
}): Promise<UserSummary> {
  return apiFetch<UserSummary>("/api/admin/users", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function setUserModuleAccess(userId: number, moduleKeys: string[]): Promise<UserSummary> {
  return apiFetch<UserSummary>(`/api/admin/users/${userId}/access`, {
    method: "PUT",
    body: JSON.stringify({ module_keys: moduleKeys }),
  });
}

export function deleteUser(userId: number): Promise<void> {
  return apiFetch<void>(`/api/admin/users/${userId}`, { method: "DELETE" });
}

// --- Master data (super-admin-only) -----------------------------------

export function listSeasons(): Promise<Season[]> {
  return apiFetch<Season[]>("/api/admin/master-data/seasons");
}

export function createSeason(name: string): Promise<Season> {
  return apiFetch<Season>("/api/admin/master-data/seasons", {
    method: "POST",
    body: JSON.stringify({ name }),
  });
}

export function updateSeason(seasonId: number, name: string): Promise<Season> {
  return apiFetch<Season>(`/api/admin/master-data/seasons/${seasonId}`, {
    method: "PUT",
    body: JSON.stringify({ name }),
  });
}

export function deleteSeason(seasonId: number): Promise<void> {
  return apiFetch<void>(`/api/admin/master-data/seasons/${seasonId}`, { method: "DELETE" });
}
