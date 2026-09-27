// Typed calls to the phone API's module endpoints (everything under
// /api/mobile/v1 except login, which lives in api.ts). Rights are enforced
// by the backend: a call the user's web role doesn't allow comes back as a
// 403 ApiError.

import { apiErrorFrom, authedFetch } from "./api";
import type {
  Dashboard,
  InterventionRequest,
  InterventionRequestInput,
  Groundplan,
  KarAction,
  KarActionInput,
  KarMapData,
  KarPlanningReport,
  KarScan,
  KarStatusOption,
  Lookups,
  Module2Permissions,
  Module3Permissions,
  ModuleInfo,
  Season,
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

const MODULE_2 = "/api/mobile/v1/module-2";

// KarTracker (module-2): only KarScan — look up a scanned kar, log a movement. No delete.
export const module2Api = {
  permissions: () => getJson<Module2Permissions>(`${MODULE_2}/permissions`),
  statuses: () => getJson<KarStatusOption[]>(`${MODULE_2}/kar-statuses`),
  // The scanned QR text is the kar number; encoded so any character is safe in the URL.
  karByNummer: (karNummer: string) =>
    getJson<KarScan>(`${MODULE_2}/karren/by-nummer/${encodeURIComponent(karNummer)}`),
  createAction: (input: KarActionInput) => sendJson<KarAction>("POST", `${MODULE_2}/kar-actions`, input),
  // Kar Planning: open seasons + the report (festival columns only with a season).
  seasons: () => getJson<Season[]>(`${MODULE_2}/seasons`),
  karPlanning: (seasonId: number | null) =>
    getJson<KarPlanningReport>(`${MODULE_2}/kar-planning${seasonId !== null ? `?season_id=${seasonId}` : ""}`),
  // Kar Map: the pins, and the ground plans overlaid on the map.
  karMap: () => getJson<KarMapData>(`${MODULE_2}/kar-map`),
  groundplans: () => getJson<Groundplan[]>(`${MODULE_2}/groundplans`),
  groundplanImage: (id: number) => getDataUri(`${MODULE_2}/groundplans/${id}/image`),
};

// GET an image with the login token and return it as a "data:" URI, so the
// map's WebView can show it without needing the token itself.
async function getDataUri(path: string): Promise<string> {
  const response = await authedFetch(path);
  if (!response.ok) throw await apiErrorFrom(response);
  const blob = await response.blob();
  return await new Promise<string>((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result));
    reader.onerror = () => reject(new Error("Could not read image"));
    reader.readAsDataURL(blob);
  });
}

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
