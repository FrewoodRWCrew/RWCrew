// Typed calls to the phone API's module endpoints (everything under
// /api/mobile/v1 except login, which lives in api.ts). Rights are enforced
// by the backend: a call the user's web role doesn't allow comes back as a
// 403 ApiError.

import { apiErrorFrom, authedFetch } from "./api";
import type {
  Dashboard,
  InterventionRequest,
  InterventionRequestInput,
  Lookups,
  Module3Permissions,
  ModuleInfo,
} from "./types";

// GET and return the JSON body, or throw an ApiError.
async function getJson<T>(path: string): Promise<T> {
  const response = await authedFetch(path);
  if (!response.ok) throw await apiErrorFrom(response);
  return (await response.json()) as T;
}

// POST/PUT a JSON body and return the JSON answer, or throw an ApiError.
async function sendJson<T>(method: "POST" | "PUT", path: string, body: unknown): Promise<T> {
  const response = await authedFetch(path, { method, body: JSON.stringify(body) });
  if (!response.ok) throw await apiErrorFrom(response);
  return (await response.json()) as T;
}

// The landing page's tiles: modules this user may open on the phone.
export const listModules = () => getJson<ModuleInfo[]>("/api/mobile/v1/modules");

const MODULE_3 = "/api/mobile/v1/module-3";

// Intervention Requests (module-3): only KPI overview + requests, no delete/PDF.
export const module3Api = {
  permissions: () => getJson<Module3Permissions>(`${MODULE_3}/permissions`),
  dashboard: () => getJson<Dashboard>(`${MODULE_3}/dashboard`),
  lookups: () => getJson<Lookups>(`${MODULE_3}/lookups`),
  listRequests: () => getJson<InterventionRequest[]>(`${MODULE_3}/intervention-requests`),
  getRequest: (id: number) => getJson<InterventionRequest>(`${MODULE_3}/intervention-requests/${id}`),
  createRequest: (input: InterventionRequestInput) =>
    sendJson<InterventionRequest>("POST", `${MODULE_3}/intervention-requests`, input),
  updateRequest: (id: number, input: InterventionRequestInput) =>
    sendJson<InterventionRequest>("PUT", `${MODULE_3}/intervention-requests/${id}`, input),
};
