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
  AfleverlocatieImportResponse,
  AltsienKernlid,
  DeliveryMethod,
  DeliveryMethodImportResponse,
  DistributiepuntImportResponse,
  Festival,
  FestivalImportResponse,
  FestivalInput,
  InterventionRequest,
  InterventionRequestInput,
  InterventionRequestsDashboardStats,
  InterventionRequestsMyPermissions,
  InterventionRequestsRole,
  InterventionRequestsScreen,
  InterventionRequestsTeam,
  InterventionRequestsUserSummary,
  InterventionStatus,
  InterventionStatusInput,
  KarImportResponse,
  KarStatusImportResponse,
  KarTrackerAfleverlocatie,
  KarTrackerAfleverlocatieInput,
  KarTrackerDistributiepunt,
  KarTrackerDistributiepuntInput,
  KarTrackerGroundplan,
  KarTrackerKar,
  KarTrackerKarInput,
  KarTrackerKarMapResponse,
  KarTrackerKarPlanningReport,
  KarTrackerKarStatus,
  KarTrackerLeverdatum,
  KarTrackerLeverdatumSaveInput,
  KarTrackerMyPermissions,
  KarTrackerPlanKar,
  KarTrackerPlanKarAfleverlocatieOption,
  KarTrackerPlanKarOption,
  KarTrackerPlanKarSaveInput,
  KarTrackerRole,
  KarTrackerScreen,
  KarTrackerUserSummary,
  KarTrackerZone,
  LoginHistoryPage,
  MasterDataDashboardStats,
  MasterDataMyPermissions,
  MasterDataRole,
  MasterDataScreen,
  MasterDataUserSummary,
  Product,
  ProductCategory,
  ProductCategoryImportResponse,
  ProductImportResponse,
  ProductInput,
  ProductLimit,
  ProductLimitImportResponse,
  ProductType,
  ProductTypeImportResponse,
  PublicInterventionRequestInput,
  RfidTag,
  RfidTagImportResponse,
  RfidTagInput,
  Scanner,
  ScannerApiKey,
  ScannerInput,
  Season,
  SeasonInput,
  SeasonImportResponse,
  TagDashboardStats,
  TagHeaderDataEntry,
  TagHeaderDataScanResult,
  TagLineDataEntry,
  TagLineDataSyncResult,
  TagscanFileContent,
  TagscanFileEntry,
  TagscanFolderNode,
  TagscanMyPermissions,
  TagscanRole,
  TagscanScreen,
  TagscanSettings,
  TagscanUserSummary,
  Team,
  TeamImportResponse,
  TeamInput,
  TeamKarMemberOption,
  TeamKarUser,
  TeamLocation,
  TeamLocationImportResponse,
  TeamTask,
  TeamTaskImportResponse,
  UserSummary,
  Warehouse,
  WarehouseImportResponse,
  ZoneImportResponse,
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

// The refresh call currently in flight, if any. Several requests often hit
// an expired session at the same moment; they must share ONE refresh,
// because the backend rotates the refresh token on every use and would
// reject the second caller's (already rotated-away) copy.
let refreshInFlight: Promise<boolean> | null = null;

/** Ask the backend for a new access token using the refresh cookie. True on success. */
function refreshSessionInBrowser(): Promise<boolean> {
  if (refreshInFlight === null) {
    refreshInFlight = fetch(`${API_BASE_URL}/api/auth/refresh`, { method: "POST", credentials: "include" })
      .then((response) => response.ok)
      .catch(() => false)
      .finally(() => {
        refreshInFlight = null;
      });
  }
  return refreshInFlight;
}

/**
 * Like fetch, but when the backend answers 401 (the 15-minute access
 * token expired) it silently renews the session once and repeats the
 * request, so the user isn't sent back to the login screen while the
 * refresh token (max 6 h since login) is still valid. Login and public endpoints are left
 * alone: a 401 there is a real answer (e.g. wrong password), not an expiry.
 */
async function fetchWithRefresh(url: string, init: RequestInit): Promise<Response> {
  const response = await fetch(url, init);
  const isAuthEndpoint = /\/api\/auth\/(login|logout|refresh)$/.test(url);
  if (response.status !== 401 || isAuthEndpoint || url.includes("/api/public/")) {
    return response;
  }

  // Still 401 after refreshing (or refreshing failed): return that answer as-is.
  if (!(await refreshSessionInBrowser())) {
    return response;
  }
  return fetch(url, init);
}

/**
 * Send one request to the backend and return its parsed JSON response.
 *
 * "credentials: include" is essential here: it tells the browser to
 * attach our login cookies to the request, and to store any new cookies
 * the backend sends back (e.g. right after logging in).
 */
async function apiFetch<TResponse>(path: string, init?: RequestInit): Promise<TResponse> {
  const response = await fetchWithRefresh(`${API_BASE_URL}${path}`, {
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

/** Change the logged-in user's own password (their other sessions are ended). */
export function changePassword(currentPassword: string, newPassword: string): Promise<CurrentUser> {
  return apiFetch<CurrentUser>("/api/auth/change-password", {
    method: "POST",
    body: JSON.stringify({ current_password: currentPassword, new_password: newPassword }),
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
  is_altsien_kernlid: boolean;
  phone: string | null;
}): Promise<UserSummary> {
  return apiFetch<UserSummary>("/api/admin/users", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function updateUser(
  userId: number,
  payload: { is_super_admin?: boolean; is_altsien_kernlid?: boolean; phone?: string | null; password?: string },
): Promise<UserSummary> {
  return apiFetch<UserSummary>(`/api/admin/users/${userId}`, {
    method: "PATCH",
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

export function listLoginHistory(params: {
  page: number;
  pageSize: number;
  dateFrom?: string;
  dateTo?: string;
}): Promise<LoginHistoryPage> {
  const query = new URLSearchParams({ page: String(params.page), page_size: String(params.pageSize) });
  if (params.dateFrom) query.set("date_from", params.dateFrom);
  if (params.dateTo) query.set("date_to", params.dateTo);
  return apiFetch<LoginHistoryPage>(`/api/admin/login-history?${query}`);
}

// --- Season (module-9's "masterdata.season" screen) ---------------------

export function listSeasons(): Promise<Season[]> {
  return apiFetch<Season[]>("/api/modules/module-9/seasons");
}

export function createSeason(payload: SeasonInput): Promise<Season> {
  return apiFetch<Season>("/api/modules/module-9/seasons", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function updateSeason(seasonId: number, payload: SeasonInput): Promise<Season> {
  return apiFetch<Season>(`/api/modules/module-9/seasons/${seasonId}`, {
    method: "PUT",
    body: JSON.stringify(payload),
  });
}

export function deleteSeason(seasonId: number): Promise<void> {
  return apiFetch<void>(`/api/modules/module-9/seasons/${seasonId}`, { method: "DELETE" });
}

// --- Team Location (module-9's "masterdata.team-location" screen, nested under Teams) ---

export function listTeamLocations(): Promise<TeamLocation[]> {
  return apiFetch<TeamLocation[]>("/api/modules/module-9/team-locations");
}

export function createTeamLocation(location: string): Promise<TeamLocation> {
  return apiFetch<TeamLocation>("/api/modules/module-9/team-locations", {
    method: "POST",
    body: JSON.stringify({ location }),
  });
}

export function updateTeamLocation(teamLocationId: number, location: string): Promise<TeamLocation> {
  return apiFetch<TeamLocation>(`/api/modules/module-9/team-locations/${teamLocationId}`, {
    method: "PUT",
    body: JSON.stringify({ location }),
  });
}

export function deleteTeamLocation(teamLocationId: number): Promise<void> {
  return apiFetch<void>(`/api/modules/module-9/team-locations/${teamLocationId}`, { method: "DELETE" });
}

// --- Delivery Method (module-9's "masterdata.delivery-method" screen, nested under Teams) ---

export function listDeliveryMethods(): Promise<DeliveryMethod[]> {
  return apiFetch<DeliveryMethod[]>("/api/modules/module-9/delivery-methods");
}

export function createDeliveryMethod(deliveryMethod: string): Promise<DeliveryMethod> {
  return apiFetch<DeliveryMethod>("/api/modules/module-9/delivery-methods", {
    method: "POST",
    body: JSON.stringify({ delivery_method: deliveryMethod }),
  });
}

export function updateDeliveryMethod(deliveryMethodId: number, deliveryMethod: string): Promise<DeliveryMethod> {
  return apiFetch<DeliveryMethod>(`/api/modules/module-9/delivery-methods/${deliveryMethodId}`, {
    method: "PUT",
    body: JSON.stringify({ delivery_method: deliveryMethod }),
  });
}

export function deleteDeliveryMethod(deliveryMethodId: number): Promise<void> {
  return apiFetch<void>(`/api/modules/module-9/delivery-methods/${deliveryMethodId}`, { method: "DELETE" });
}

// --- Team Tasks (module-9's "masterdata.team-tasks" screen, nested under Teams) ---

export function listTeamTasks(): Promise<TeamTask[]> {
  return apiFetch<TeamTask[]>("/api/modules/module-9/team-tasks");
}

export function createTeamTask(teamTasks: string): Promise<TeamTask> {
  return apiFetch<TeamTask>("/api/modules/module-9/team-tasks", {
    method: "POST",
    body: JSON.stringify({ team_tasks: teamTasks }),
  });
}

export function updateTeamTask(teamTaskId: number, teamTasks: string): Promise<TeamTask> {
  return apiFetch<TeamTask>(`/api/modules/module-9/team-tasks/${teamTaskId}`, {
    method: "PUT",
    body: JSON.stringify({ team_tasks: teamTasks }),
  });
}

export function deleteTeamTask(teamTaskId: number): Promise<void> {
  return apiFetch<void>(`/api/modules/module-9/team-tasks/${teamTaskId}`, { method: "DELETE" });
}

// --- Teams (module-9's "masterdata.teams" screen) -------------------------

export function listTeams(): Promise<Team[]> {
  return apiFetch<Team[]>("/api/modules/module-9/teams");
}

export function createTeam(payload: TeamInput): Promise<Team> {
  return apiFetch<Team>("/api/modules/module-9/teams", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function updateTeam(teamId: number, payload: TeamInput): Promise<Team> {
  return apiFetch<Team>(`/api/modules/module-9/teams/${teamId}`, {
    method: "PUT",
    body: JSON.stringify(payload),
  });
}

export function deleteTeam(teamId: number): Promise<void> {
  return apiFetch<void>(`/api/modules/module-9/teams/${teamId}`, { method: "DELETE" });
}

// --- Festivals (module-9's "masterdata.festival" screen) -----------------

export function listFestivals(): Promise<Festival[]> {
  return apiFetch<Festival[]>("/api/modules/module-9/festivals");
}

export function createFestival(payload: FestivalInput): Promise<Festival> {
  return apiFetch<Festival>("/api/modules/module-9/festivals", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function updateFestival(festivalId: number, payload: FestivalInput): Promise<Festival> {
  return apiFetch<Festival>(`/api/modules/module-9/festivals/${festivalId}`, {
    method: "PUT",
    body: JSON.stringify(payload),
  });
}

export function deleteFestival(festivalId: number): Promise<void> {
  return apiFetch<void>(`/api/modules/module-9/festivals/${festivalId}`, { method: "DELETE" });
}

// --- Altsien Kernleden: users flagged on the Manage Access screen ---

export function listAltsienKernleden(): Promise<AltsienKernlid[]> {
  return apiFetch<AltsienKernlid[]>("/api/modules/altsien-kernleden");
}

// --- Products (module-9's "masterdata.products" screen) -----------------

export function listProducts(): Promise<Product[]> {
  return apiFetch<Product[]>("/api/modules/module-9/products");
}

export function createProduct(payload: ProductInput): Promise<Product> {
  return apiFetch<Product>("/api/modules/module-9/products", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function updateProduct(productId: number, payload: ProductInput): Promise<Product> {
  return apiFetch<Product>(`/api/modules/module-9/products/${productId}`, {
    method: "PUT",
    body: JSON.stringify(payload),
  });
}

export function deleteProduct(productId: number): Promise<void> {
  return apiFetch<void>(`/api/modules/module-9/products/${productId}`, { method: "DELETE" });
}

// --- Product types (module-9's "masterdata.product-types" screen) -------

export function listProductTypes(): Promise<ProductType[]> {
  return apiFetch<ProductType[]>("/api/modules/module-9/product-types");
}

export function createProductType(name: string): Promise<ProductType> {
  return apiFetch<ProductType>("/api/modules/module-9/product-types", {
    method: "POST",
    body: JSON.stringify({ name }),
  });
}

export function updateProductType(productTypeId: number, name: string): Promise<ProductType> {
  return apiFetch<ProductType>(`/api/modules/module-9/product-types/${productTypeId}`, {
    method: "PUT",
    body: JSON.stringify({ name }),
  });
}

export function deleteProductType(productTypeId: number): Promise<void> {
  return apiFetch<void>(`/api/modules/module-9/product-types/${productTypeId}`, { method: "DELETE" });
}

// --- Warehouses (module-9's "masterdata.warehouses" screen) -------------

export function listWarehouses(): Promise<Warehouse[]> {
  return apiFetch<Warehouse[]>("/api/modules/module-9/warehouses");
}

export function createWarehouse(name: string): Promise<Warehouse> {
  return apiFetch<Warehouse>("/api/modules/module-9/warehouses", {
    method: "POST",
    body: JSON.stringify({ name }),
  });
}

export function updateWarehouse(warehouseId: number, name: string): Promise<Warehouse> {
  return apiFetch<Warehouse>(`/api/modules/module-9/warehouses/${warehouseId}`, {
    method: "PUT",
    body: JSON.stringify({ name }),
  });
}

export function deleteWarehouse(warehouseId: number): Promise<void> {
  return apiFetch<void>(`/api/modules/module-9/warehouses/${warehouseId}`, { method: "DELETE" });
}

// --- Product categories (module-9's "masterdata.product-categories" screen) ---

export function listProductCategories(): Promise<ProductCategory[]> {
  return apiFetch<ProductCategory[]>("/api/modules/module-9/product-categories");
}

export function createProductCategory(name: string): Promise<ProductCategory> {
  return apiFetch<ProductCategory>("/api/modules/module-9/product-categories", {
    method: "POST",
    body: JSON.stringify({ name }),
  });
}

export function updateProductCategory(productCategoryId: number, name: string): Promise<ProductCategory> {
  return apiFetch<ProductCategory>(`/api/modules/module-9/product-categories/${productCategoryId}`, {
    method: "PUT",
    body: JSON.stringify({ name }),
  });
}

export function deleteProductCategory(productCategoryId: number): Promise<void> {
  return apiFetch<void>(`/api/modules/module-9/product-categories/${productCategoryId}`, { method: "DELETE" });
}

// --- Product limits (module-9's "masterdata.product-limits" screen) -----

export function listProductLimits(): Promise<ProductLimit[]> {
  return apiFetch<ProductLimit[]>("/api/modules/module-9/product-limits");
}

export function createProductLimit(name: string): Promise<ProductLimit> {
  return apiFetch<ProductLimit>("/api/modules/module-9/product-limits", {
    method: "POST",
    body: JSON.stringify({ name }),
  });
}

export function updateProductLimit(productLimitId: number, name: string): Promise<ProductLimit> {
  return apiFetch<ProductLimit>(`/api/modules/module-9/product-limits/${productLimitId}`, {
    method: "PUT",
    body: JSON.stringify({ name }),
  });
}

export function deleteProductLimit(productLimitId: number): Promise<void> {
  return apiFetch<void>(`/api/modules/module-9/product-limits/${productLimitId}`, { method: "DELETE" });
}

// --- Tagscan (module-1) -------------------------------------------------

export function getTagscanMyPermissions(): Promise<TagscanMyPermissions> {
  return apiFetch<TagscanMyPermissions>("/api/modules/module-1/me/permissions");
}

export function listTagscanScreens(): Promise<TagscanScreen[]> {
  return apiFetch<TagscanScreen[]>("/api/modules/module-1/screens");
}

export function listTagscanRoles(): Promise<TagscanRole[]> {
  return apiFetch<TagscanRole[]>("/api/modules/module-1/roles");
}

export function createTagscanRole(name: string): Promise<TagscanRole> {
  return apiFetch<TagscanRole>("/api/modules/module-1/roles", {
    method: "POST",
    body: JSON.stringify({ name }),
  });
}

export function renameTagscanRole(roleId: number, name: string): Promise<TagscanRole> {
  return apiFetch<TagscanRole>(`/api/modules/module-1/roles/${roleId}`, {
    method: "PUT",
    body: JSON.stringify({ name }),
  });
}

export function deleteTagscanRole(roleId: number): Promise<void> {
  return apiFetch<void>(`/api/modules/module-1/roles/${roleId}`, { method: "DELETE" });
}

export interface TagscanPermissionUpdate {
  screen_id: number;
  can_view: boolean;
  can_create: boolean;
  can_edit: boolean;
  can_delete: boolean;
}

export function setTagscanRolePermissions(
  roleId: number,
  permissions: TagscanPermissionUpdate[],
): Promise<TagscanRole> {
  return apiFetch<TagscanRole>(`/api/modules/module-1/roles/${roleId}/permissions`, {
    method: "PUT",
    body: JSON.stringify({ permissions }),
  });
}

export function listTagscanUsers(): Promise<TagscanUserSummary[]> {
  return apiFetch<TagscanUserSummary[]>("/api/modules/module-1/users");
}

export function setTagscanUserRole(userId: number, roleId: number | null): Promise<TagscanUserSummary> {
  return apiFetch<TagscanUserSummary>(`/api/modules/module-1/users/${userId}/role`, {
    method: "PUT",
    body: JSON.stringify({ role_id: roleId }),
  });
}

export function createOrGrantTagscanUser(payload: {
  email: string;
  display_name?: string;
  password?: string;
  role_id?: number | null;
}): Promise<TagscanUserSummary> {
  return apiFetch<TagscanUserSummary>("/api/modules/module-1/users", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function getTagscanFolderTree(): Promise<TagscanFolderNode> {
  return apiFetch<TagscanFolderNode>("/api/modules/module-1/files/tree");
}

export function listTagscanFiles(path: string): Promise<TagscanFileEntry[]> {
  return apiFetch<TagscanFileEntry[]>(`/api/modules/module-1/files?path=${encodeURIComponent(path)}`);
}

export function getTagscanFileContent(path: string): Promise<TagscanFileContent> {
  return apiFetch<TagscanFileContent>(`/api/modules/module-1/files/content?path=${encodeURIComponent(path)}`);
}

// --- Tag Headerdata (module-1's "tagscan.tag-headerdata" screen) --------

export function listTagHeaderData(): Promise<TagHeaderDataEntry[]> {
  return apiFetch<TagHeaderDataEntry[]>("/api/modules/module-1/header-data");
}

export function scanTagHeaderData(): Promise<TagHeaderDataScanResult> {
  return apiFetch<TagHeaderDataScanResult>("/api/modules/module-1/header-data/scan", { method: "POST" });
}

export function deleteTagHeaderData(headerId: number): Promise<void> {
  return apiFetch<void>(`/api/modules/module-1/header-data/${headerId}`, { method: "DELETE" });
}

// --- Tag Linedata (module-1's "tagscan.tag-linedata" screen) ------------

export function listTagLineData(): Promise<TagLineDataEntry[]> {
  return apiFetch<TagLineDataEntry[]>("/api/modules/module-1/line-data");
}

export function cancelTagLineData(lineId: number): Promise<TagLineDataEntry> {
  return apiFetch<TagLineDataEntry>(`/api/modules/module-1/line-data/${lineId}/cancel`, { method: "POST" });
}

export function syncTagLineData(): Promise<TagLineDataSyncResult> {
  return apiFetch<TagLineDataSyncResult>("/api/modules/module-1/line-data/sync", { method: "POST" });
}

// --- RFID tags (module-1's "tagscan.tag-management" screen) -------------

export function listRfidTags(): Promise<RfidTag[]> {
  return apiFetch<RfidTag[]>("/api/modules/module-1/tags");
}

export function createRfidTag(payload: RfidTagInput): Promise<RfidTag> {
  return apiFetch<RfidTag>("/api/modules/module-1/tags", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function updateRfidTag(tagId: number, payload: RfidTagInput): Promise<RfidTag> {
  return apiFetch<RfidTag>(`/api/modules/module-1/tags/${tagId}`, {
    method: "PUT",
    body: JSON.stringify(payload),
  });
}

export function deleteRfidTag(tagId: number): Promise<void> {
  return apiFetch<void>(`/api/modules/module-1/tags/${tagId}`, { method: "DELETE" });
}

// --- Scanners (module-1's "tagscan.scanners" screen) ---------------------

export function listScanners(): Promise<Scanner[]> {
  return apiFetch<Scanner[]>("/api/modules/module-1/scanners");
}

export function createScanner(payload: ScannerInput): Promise<Scanner> {
  return apiFetch<Scanner>("/api/modules/module-1/scanners", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function updateScanner(scannerId: number, payload: ScannerInput): Promise<Scanner> {
  return apiFetch<Scanner>(`/api/modules/module-1/scanners/${scannerId}`, {
    method: "PUT",
    body: JSON.stringify(payload),
  });
}

export function deleteScanner(scannerId: number): Promise<void> {
  return apiFetch<void>(`/api/modules/module-1/scanners/${scannerId}`, { method: "DELETE" });
}

/** Generates a brand-new device CSV-intake API key for a scanner,
 * invalidating any previous one. The plaintext key is only ever returned
 * here, once — see components/module-1/scanner-management.tsx's reveal dialog. */
export function generateScannerApiKey(scannerId: number): Promise<ScannerApiKey> {
  return apiFetch<ScannerApiKey>(`/api/modules/module-1/scanners/${scannerId}/api-key`, { method: "POST" });
}

export function revokeScannerApiKey(scannerId: number): Promise<void> {
  return apiFetch<void>(`/api/modules/module-1/scanners/${scannerId}/api-key`, { method: "DELETE" });
}

// --- Settings (module-1's "tagscan.settings" screen) ----------------------

export function getTagscanSettings(): Promise<TagscanSettings> {
  return apiFetch<TagscanSettings>("/api/modules/module-1/settings");
}

export function updateTagscanSettings(payload: TagscanSettings): Promise<TagscanSettings> {
  return apiFetch<TagscanSettings>("/api/modules/module-1/settings", {
    method: "PUT",
    body: JSON.stringify({ receive_folder_path: payload.receive_folder_path }),
  });
}

/**
 * Uploads a CSV file to bulk-import tags. Uses a plain fetch instead of
 * apiFetch: the body is FormData, not JSON, and the browser must set its
 * own multipart Content-Type (with boundary) — setting it manually would
 * break the upload.
 */
export async function importRfidTags(file: File): Promise<RfidTagImportResponse> {
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetchWithRefresh(`${API_BASE_URL}/api/modules/module-1/tags/import`, {
    method: "POST",
    credentials: "include",
    body: formData,
  });

  if (!response.ok) {
    const errorBody = await response.json().catch(() => null);
    const message = errorBody?.detail ?? `Request failed with status ${response.status}`;
    throw new ApiError(message, response.status);
  }

  return (await response.json()) as RfidTagImportResponse;
}

export function getTagDashboardStats(): Promise<TagDashboardStats> {
  return apiFetch<TagDashboardStats>("/api/modules/module-1/dashboard");
}

// --- MasterData (module-9) -------------------------------------------------

export function getMasterDataDashboardStats(): Promise<MasterDataDashboardStats> {
  return apiFetch<MasterDataDashboardStats>("/api/modules/module-9/dashboard");
}

export function getMasterDataMyPermissions(): Promise<MasterDataMyPermissions> {
  return apiFetch<MasterDataMyPermissions>("/api/modules/module-9/me/permissions");
}

export function listMasterDataScreens(): Promise<MasterDataScreen[]> {
  return apiFetch<MasterDataScreen[]>("/api/modules/module-9/screens");
}

export function listMasterDataRoles(): Promise<MasterDataRole[]> {
  return apiFetch<MasterDataRole[]>("/api/modules/module-9/roles");
}

export function createMasterDataRole(name: string): Promise<MasterDataRole> {
  return apiFetch<MasterDataRole>("/api/modules/module-9/roles", {
    method: "POST",
    body: JSON.stringify({ name }),
  });
}

export function renameMasterDataRole(roleId: number, name: string): Promise<MasterDataRole> {
  return apiFetch<MasterDataRole>(`/api/modules/module-9/roles/${roleId}`, {
    method: "PUT",
    body: JSON.stringify({ name }),
  });
}

export function deleteMasterDataRole(roleId: number): Promise<void> {
  return apiFetch<void>(`/api/modules/module-9/roles/${roleId}`, { method: "DELETE" });
}

export interface MasterDataPermissionUpdate {
  screen_id: number;
  can_view: boolean;
  can_create: boolean;
  can_edit: boolean;
  can_delete: boolean;
}

export function setMasterDataRolePermissions(
  roleId: number,
  permissions: MasterDataPermissionUpdate[],
): Promise<MasterDataRole> {
  return apiFetch<MasterDataRole>(`/api/modules/module-9/roles/${roleId}/permissions`, {
    method: "PUT",
    body: JSON.stringify({ permissions }),
  });
}

export function listMasterDataUsers(): Promise<MasterDataUserSummary[]> {
  return apiFetch<MasterDataUserSummary[]>("/api/modules/module-9/users");
}

export function setMasterDataUserRole(userId: number, roleId: number | null): Promise<MasterDataUserSummary> {
  return apiFetch<MasterDataUserSummary>(`/api/modules/module-9/users/${userId}/role`, {
    method: "PUT",
    body: JSON.stringify({ role_id: roleId }),
  });
}

export function createOrGrantMasterDataUser(payload: {
  email: string;
  display_name?: string;
  password?: string;
  role_id?: number | null;
}): Promise<MasterDataUserSummary> {
  return apiFetch<MasterDataUserSummary>("/api/modules/module-9/users", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

// --- MasterData (module-9): Data Upload/Download ---------------------------
//
// Each uses a plain fetch instead of apiFetch: the body is FormData, not
// JSON, and the browser must set its own multipart Content-Type (with
// boundary) — setting it manually would break the upload. Mirrors
// importKarren/importKarStatuses above.

export async function importSeasons(file: File): Promise<SeasonImportResponse> {
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetchWithRefresh(`${API_BASE_URL}/api/modules/module-9/season-import`, {
    method: "POST",
    credentials: "include",
    body: formData,
  });

  if (!response.ok) {
    const errorBody = await response.json().catch(() => null);
    const message = errorBody?.detail ?? `Request failed with status ${response.status}`;
    throw new ApiError(message, response.status);
  }

  return (await response.json()) as SeasonImportResponse;
}

export async function importProductTypes(file: File): Promise<ProductTypeImportResponse> {
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetchWithRefresh(`${API_BASE_URL}/api/modules/module-9/product-type-import`, {
    method: "POST",
    credentials: "include",
    body: formData,
  });

  if (!response.ok) {
    const errorBody = await response.json().catch(() => null);
    const message = errorBody?.detail ?? `Request failed with status ${response.status}`;
    throw new ApiError(message, response.status);
  }

  return (await response.json()) as ProductTypeImportResponse;
}

export async function importWarehouses(file: File): Promise<WarehouseImportResponse> {
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetchWithRefresh(`${API_BASE_URL}/api/modules/module-9/warehouse-import`, {
    method: "POST",
    credentials: "include",
    body: formData,
  });

  if (!response.ok) {
    const errorBody = await response.json().catch(() => null);
    const message = errorBody?.detail ?? `Request failed with status ${response.status}`;
    throw new ApiError(message, response.status);
  }

  return (await response.json()) as WarehouseImportResponse;
}

export async function importProductCategories(file: File): Promise<ProductCategoryImportResponse> {
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetchWithRefresh(`${API_BASE_URL}/api/modules/module-9/product-category-import`, {
    method: "POST",
    credentials: "include",
    body: formData,
  });

  if (!response.ok) {
    const errorBody = await response.json().catch(() => null);
    const message = errorBody?.detail ?? `Request failed with status ${response.status}`;
    throw new ApiError(message, response.status);
  }

  return (await response.json()) as ProductCategoryImportResponse;
}

export async function importProductLimits(file: File): Promise<ProductLimitImportResponse> {
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetchWithRefresh(`${API_BASE_URL}/api/modules/module-9/product-limit-import`, {
    method: "POST",
    credentials: "include",
    body: formData,
  });

  if (!response.ok) {
    const errorBody = await response.json().catch(() => null);
    const message = errorBody?.detail ?? `Request failed with status ${response.status}`;
    throw new ApiError(message, response.status);
  }

  return (await response.json()) as ProductLimitImportResponse;
}

export async function importTeamLocations(file: File): Promise<TeamLocationImportResponse> {
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetchWithRefresh(`${API_BASE_URL}/api/modules/module-9/team-location-import`, {
    method: "POST",
    credentials: "include",
    body: formData,
  });

  if (!response.ok) {
    const errorBody = await response.json().catch(() => null);
    const message = errorBody?.detail ?? `Request failed with status ${response.status}`;
    throw new ApiError(message, response.status);
  }

  return (await response.json()) as TeamLocationImportResponse;
}

export async function importDeliveryMethods(file: File): Promise<DeliveryMethodImportResponse> {
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetchWithRefresh(`${API_BASE_URL}/api/modules/module-9/delivery-method-import`, {
    method: "POST",
    credentials: "include",
    body: formData,
  });

  if (!response.ok) {
    const errorBody = await response.json().catch(() => null);
    const message = errorBody?.detail ?? `Request failed with status ${response.status}`;
    throw new ApiError(message, response.status);
  }

  return (await response.json()) as DeliveryMethodImportResponse;
}

export async function importTeamTasks(file: File): Promise<TeamTaskImportResponse> {
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetchWithRefresh(`${API_BASE_URL}/api/modules/module-9/team-task-import`, {
    method: "POST",
    credentials: "include",
    body: formData,
  });

  if (!response.ok) {
    const errorBody = await response.json().catch(() => null);
    const message = errorBody?.detail ?? `Request failed with status ${response.status}`;
    throw new ApiError(message, response.status);
  }

  return (await response.json()) as TeamTaskImportResponse;
}

export async function importFestivals(file: File): Promise<FestivalImportResponse> {
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetchWithRefresh(`${API_BASE_URL}/api/modules/module-9/festival-import`, {
    method: "POST",
    credentials: "include",
    body: formData,
  });

  if (!response.ok) {
    const errorBody = await response.json().catch(() => null);
    const message = errorBody?.detail ?? `Request failed with status ${response.status}`;
    throw new ApiError(message, response.status);
  }

  return (await response.json()) as FestivalImportResponse;
}

export async function importProducts(file: File): Promise<ProductImportResponse> {
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetchWithRefresh(`${API_BASE_URL}/api/modules/module-9/product-import`, {
    method: "POST",
    credentials: "include",
    body: formData,
  });

  if (!response.ok) {
    const errorBody = await response.json().catch(() => null);
    const message = errorBody?.detail ?? `Request failed with status ${response.status}`;
    throw new ApiError(message, response.status);
  }

  return (await response.json()) as ProductImportResponse;
}

/** Only imports Team's scalar fields — task/kernlid links are not part of
 * this bulk tool, see team_import.py on the backend. */
export async function importTeams(file: File): Promise<TeamImportResponse> {
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetchWithRefresh(`${API_BASE_URL}/api/modules/module-9/team-import`, {
    method: "POST",
    credentials: "include",
    body: formData,
  });

  if (!response.ok) {
    const errorBody = await response.json().catch(() => null);
    const message = errorBody?.detail ?? `Request failed with status ${response.status}`;
    throw new ApiError(message, response.status);
  }

  return (await response.json()) as TeamImportResponse;
}

// --- Intervention Requests (module-3): KPI landing dashboard ---------------

export function getInterventionRequestsDashboard(): Promise<InterventionRequestsDashboardStats> {
  return apiFetch<InterventionRequestsDashboardStats>("/api/modules/module-3/dashboard");
}

// --- Intervention Requests (module-3): custom roles with per-screen permissions ---

export function getInterventionRequestsMyPermissions(): Promise<InterventionRequestsMyPermissions> {
  return apiFetch<InterventionRequestsMyPermissions>("/api/modules/module-3/me/permissions");
}

export function listInterventionRequestsScreens(): Promise<InterventionRequestsScreen[]> {
  return apiFetch<InterventionRequestsScreen[]>("/api/modules/module-3/screens");
}

export function listInterventionRequestsRoles(): Promise<InterventionRequestsRole[]> {
  return apiFetch<InterventionRequestsRole[]>("/api/modules/module-3/roles");
}

export function createInterventionRequestsRole(name: string): Promise<InterventionRequestsRole> {
  return apiFetch<InterventionRequestsRole>("/api/modules/module-3/roles", {
    method: "POST",
    body: JSON.stringify({ name }),
  });
}

export function renameInterventionRequestsRole(roleId: number, name: string): Promise<InterventionRequestsRole> {
  return apiFetch<InterventionRequestsRole>(`/api/modules/module-3/roles/${roleId}`, {
    method: "PUT",
    body: JSON.stringify({ name }),
  });
}

export function deleteInterventionRequestsRole(roleId: number): Promise<void> {
  return apiFetch<void>(`/api/modules/module-3/roles/${roleId}`, { method: "DELETE" });
}

export interface InterventionRequestsPermissionUpdate {
  screen_id: number;
  can_view: boolean;
  can_create: boolean;
  can_edit: boolean;
  can_delete: boolean;
}

export function setInterventionRequestsRolePermissions(
  roleId: number,
  permissions: InterventionRequestsPermissionUpdate[],
): Promise<InterventionRequestsRole> {
  return apiFetch<InterventionRequestsRole>(`/api/modules/module-3/roles/${roleId}/permissions`, {
    method: "PUT",
    body: JSON.stringify({ permissions }),
  });
}

export function listInterventionRequestsUsers(): Promise<InterventionRequestsUserSummary[]> {
  return apiFetch<InterventionRequestsUserSummary[]>("/api/modules/module-3/users");
}

export function setInterventionRequestsUserRole(
  userId: number,
  roleId: number | null,
): Promise<InterventionRequestsUserSummary> {
  return apiFetch<InterventionRequestsUserSummary>(`/api/modules/module-3/users/${userId}/role`, {
    method: "PUT",
    body: JSON.stringify({ role_id: roleId }),
  });
}

export function createOrGrantInterventionRequestsUser(payload: {
  email: string;
  display_name?: string;
  password?: string;
  role_id?: number | null;
}): Promise<InterventionRequestsUserSummary> {
  return apiFetch<InterventionRequestsUserSummary>("/api/modules/module-3/users", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

// --- KarTracker (module-2): custom roles with per-screen permissions ---
//
// This is the module's first development phase — only the Access Rights
// scaffold exists so far (Roles + Users). Business-specific endpoints
// (cart registry/"Karlijst", delivery planning, ...) get added here once
// those screens are designed in a later phase.

export function getKarTrackerMyPermissions(): Promise<KarTrackerMyPermissions> {
  return apiFetch<KarTrackerMyPermissions>("/api/modules/module-2/me/permissions");
}

export function listKarTrackerScreens(): Promise<KarTrackerScreen[]> {
  return apiFetch<KarTrackerScreen[]>("/api/modules/module-2/screens");
}

export function getKarTrackerGroundplan(): Promise<KarTrackerGroundplan> {
  return apiFetch<KarTrackerGroundplan>("/api/modules/module-2/groundplan");
}

/**
 * Saves the ground plan's corner coordinates, and its image if a new one
 * was picked. Uses a plain fetch instead of apiFetch, same reason as
 * importKarren below: the body is FormData (an optional file plus four
 * numeric fields), and the browser must set its own multipart
 * Content-Type (with boundary) — setting it manually would break the
 * upload.
 */
export async function updateKarTrackerGroundplan(formData: FormData): Promise<KarTrackerGroundplan> {
  const response = await fetchWithRefresh(`${API_BASE_URL}/api/modules/module-2/groundplan`, {
    method: "PUT",
    credentials: "include",
    body: formData,
  });

  if (!response.ok) {
    const errorBody = await response.json().catch(() => null);
    const message = errorBody?.detail ?? `Request failed with status ${response.status}`;
    throw new ApiError(message, response.status);
  }

  return (await response.json()) as KarTrackerGroundplan;
}

/** The ground plan image's direct URL, for use as an <img>/Leaflet
 * ImageOverlay source — the browser sends the auth cookie automatically
 * since the frontend and backend are always same-site, so no fetch-and-
 * blob round trip is needed here. */
export function karTrackerGroundplanImageUrl(): string {
  return `${API_BASE_URL}/api/modules/module-2/groundplan/image`;
}

// "Plan a kar": per team, one delivery location per active festival of a season.

/** The active teams offered in the "Plan a kar" team dropdown. */
export function listPlanKarTeams(): Promise<KarTrackerPlanKarOption[]> {
  return apiFetch<KarTrackerPlanKarOption[]>("/api/modules/module-2/plan-kar/teams");
}

/** The active delivery locations offered in every "Plan a kar" row. */
export function listPlanKarAfleverlocaties(): Promise<KarTrackerPlanKarAfleverlocatieOption[]> {
  return apiFetch<KarTrackerPlanKarAfleverlocatieOption[]>("/api/modules/module-2/plan-kar/afleverlocaties");
}

/** The matrix (active festivals of the season + saved locations) for one team. */
export function getPlanKar(seasonId: number, teamId: number): Promise<KarTrackerPlanKar> {
  return apiFetch<KarTrackerPlanKar>(`/api/modules/module-2/plan-kar?season_id=${seasonId}&team_id=${teamId}`);
}

/** Saves the whole matrix; existing (season, festival, team) records are updated, not duplicated. */
export function savePlanKar(payload: KarTrackerPlanKarSaveInput): Promise<KarTrackerPlanKar> {
  return apiFetch<KarTrackerPlanKar>("/api/modules/module-2/plan-kar", {
    method: "PUT",
    body: JSON.stringify(payload),
  });
}

/** The "Delivery Dates" table: active festivals of the season + their saved dates. */
export function getLeverdata(seasonId: number): Promise<KarTrackerLeverdatum> {
  return apiFetch<KarTrackerLeverdatum>(`/api/modules/module-2/leverdata?season_id=${seasonId}`);
}

/** Saves the whole table; existing per-festival records are updated, not duplicated. */
export function saveLeverdata(payload: KarTrackerLeverdatumSaveInput): Promise<KarTrackerLeverdatum> {
  return apiFetch<KarTrackerLeverdatum>("/api/modules/module-2/leverdata", {
    method: "PUT",
    body: JSON.stringify(payload),
  });
}

export function listKarTrackerRoles(): Promise<KarTrackerRole[]> {
  return apiFetch<KarTrackerRole[]>("/api/modules/module-2/roles");
}

export function createKarTrackerRole(name: string): Promise<KarTrackerRole> {
  return apiFetch<KarTrackerRole>("/api/modules/module-2/roles", {
    method: "POST",
    body: JSON.stringify({ name }),
  });
}

export function renameKarTrackerRole(roleId: number, name: string): Promise<KarTrackerRole> {
  return apiFetch<KarTrackerRole>(`/api/modules/module-2/roles/${roleId}`, {
    method: "PUT",
    body: JSON.stringify({ name }),
  });
}

export function deleteKarTrackerRole(roleId: number): Promise<void> {
  return apiFetch<void>(`/api/modules/module-2/roles/${roleId}`, { method: "DELETE" });
}

export interface KarTrackerPermissionUpdate {
  screen_id: number;
  can_view: boolean;
  can_create: boolean;
  can_edit: boolean;
  can_delete: boolean;
}

export function setKarTrackerRolePermissions(
  roleId: number,
  permissions: KarTrackerPermissionUpdate[],
): Promise<KarTrackerRole> {
  return apiFetch<KarTrackerRole>(`/api/modules/module-2/roles/${roleId}/permissions`, {
    method: "PUT",
    body: JSON.stringify({ permissions }),
  });
}

export function listKarTrackerUsers(): Promise<KarTrackerUserSummary[]> {
  return apiFetch<KarTrackerUserSummary[]>("/api/modules/module-2/users");
}

export function setKarTrackerUserRole(userId: number, roleId: number | null): Promise<KarTrackerUserSummary> {
  return apiFetch<KarTrackerUserSummary>(`/api/modules/module-2/users/${userId}/role`, {
    method: "PUT",
    body: JSON.stringify({ role_id: roleId }),
  });
}

export function createOrGrantKarTrackerUser(payload: {
  email: string;
  display_name?: string;
  password?: string;
  role_id?: number | null;
}): Promise<KarTrackerUserSummary> {
  return apiFetch<KarTrackerUserSummary>("/api/modules/module-2/users", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

// --- KarStatussen (module-2's "kartracker.karstatuses" lookup screen) ---

export function listKarStatuses(): Promise<KarTrackerKarStatus[]> {
  return apiFetch<KarTrackerKarStatus[]>("/api/modules/module-2/kar-statuses");
}

export function createKarStatus(name: string): Promise<KarTrackerKarStatus> {
  return apiFetch<KarTrackerKarStatus>("/api/modules/module-2/kar-statuses", {
    method: "POST",
    body: JSON.stringify({ name }),
  });
}

export function updateKarStatus(karStatusId: number, name: string): Promise<KarTrackerKarStatus> {
  return apiFetch<KarTrackerKarStatus>(`/api/modules/module-2/kar-statuses/${karStatusId}`, {
    method: "PUT",
    body: JSON.stringify({ name }),
  });
}

export function deleteKarStatus(karStatusId: number): Promise<void> {
  return apiFetch<void>(`/api/modules/module-2/kar-statuses/${karStatusId}`, { method: "DELETE" });
}

// --- KarManagement (module-2's "kartracker.karmanagement" fleet registry) ---

export function listKarren(): Promise<KarTrackerKar[]> {
  return apiFetch<KarTrackerKar[]>("/api/modules/module-2/karren");
}

export function createKar(payload: KarTrackerKarInput): Promise<KarTrackerKar> {
  return apiFetch<KarTrackerKar>("/api/modules/module-2/karren", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function updateKar(karId: number, payload: KarTrackerKarInput): Promise<KarTrackerKar> {
  return apiFetch<KarTrackerKar>(`/api/modules/module-2/karren/${karId}`, {
    method: "PUT",
    body: JSON.stringify(payload),
  });
}

export function deleteKar(karId: number): Promise<void> {
  return apiFetch<void>(`/api/modules/module-2/karren/${karId}`, { method: "DELETE" });
}

// --- Kar Planning (module-2's "kartracker.karplanning" read-only report) ---

/** With a season id the report also carries one afleverlocatie column per active festival of it. */
export function listKarPlanning(seasonId?: number | null): Promise<KarTrackerKarPlanningReport> {
  const query = seasonId != null ? `?season_id=${seasonId}` : "";
  return apiFetch<KarTrackerKarPlanningReport>(`/api/modules/module-2/kar-planning${query}`);
}

/**
 * The Kar Planning "Print" button: asks the backend for one PDF page (a
 * "karblad") per selected kar and returns the PDF itself. `siteUrl` is the
 * public address the pages' QR codes should point to. Plain fetch because
 * the response is a binary PDF, not JSON (apiFetch would try to parse it).
 */
export async function printKarPlanning(
  seasonId: number,
  karIds: number[],
  siteUrl: string,
  locale: string,
): Promise<Blob> {
  const response = await fetchWithRefresh(`${API_BASE_URL}/api/modules/module-2/kar-planning/print`, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ season_id: seasonId, kar_ids: karIds, site_url: siteUrl, locale }),
  });

  if (!response.ok) {
    const errorBody = await response.json().catch(() => null);
    const message = typeof errorBody?.detail === "string" ? errorBody.detail : `Request failed with status ${response.status}`;
    throw new ApiError(message, response.status);
  }

  return response.blob();
}

// --- Kar Map (module-2's "kartracker.karmap" read-only map report) ---

export function listKarMap(): Promise<KarTrackerKarMapResponse> {
  return apiFetch<KarTrackerKarMapResponse>("/api/modules/module-2/kar-map");
}

/**
 * Uploads an XLSX file to bulk-register new karren. Uses a plain fetch
 * instead of apiFetch: the body is FormData, not JSON, and the browser
 * must set its own multipart Content-Type (with boundary) — setting it
 * manually would break the upload. Mirrors importRfidTags above.
 */
export async function importKarren(file: File): Promise<KarImportResponse> {
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetchWithRefresh(`${API_BASE_URL}/api/modules/module-2/kar-import`, {
    method: "POST",
    credentials: "include",
    body: formData,
  });

  if (!response.ok) {
    const errorBody = await response.json().catch(() => null);
    const message = errorBody?.detail ?? `Request failed with status ${response.status}`;
    throw new ApiError(message, response.status);
  }

  return (await response.json()) as KarImportResponse;
}

/**
 * Uploads an XLSX file to bulk-register new kar statuses. Mirrors
 * importKarren above.
 */
export async function importKarStatuses(file: File): Promise<KarStatusImportResponse> {
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetchWithRefresh(`${API_BASE_URL}/api/modules/module-2/kar-status-import`, {
    method: "POST",
    credentials: "include",
    body: formData,
  });

  if (!response.ok) {
    const errorBody = await response.json().catch(() => null);
    const message = errorBody?.detail ?? `Request failed with status ${response.status}`;
    throw new ApiError(message, response.status);
  }

  return (await response.json()) as KarStatusImportResponse;
}

// --- Distributiepunten (module-2's "kartracker.distributiepunten" master data) ---

export function listDistributiepunten(): Promise<KarTrackerDistributiepunt[]> {
  return apiFetch<KarTrackerDistributiepunt[]>("/api/modules/module-2/distributiepunten");
}

export function createDistributiepunt(payload: KarTrackerDistributiepuntInput): Promise<KarTrackerDistributiepunt> {
  return apiFetch<KarTrackerDistributiepunt>("/api/modules/module-2/distributiepunten", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function updateDistributiepunt(
  distributiepuntId: number,
  payload: KarTrackerDistributiepuntInput,
): Promise<KarTrackerDistributiepunt> {
  return apiFetch<KarTrackerDistributiepunt>(`/api/modules/module-2/distributiepunten/${distributiepuntId}`, {
    method: "PUT",
    body: JSON.stringify(payload),
  });
}

export function deleteDistributiepunt(distributiepuntId: number): Promise<void> {
  return apiFetch<void>(`/api/modules/module-2/distributiepunten/${distributiepuntId}`, { method: "DELETE" });
}

/** Uploads an XLSX file to bulk-register new distribution points. Mirrors importKarren above. */
export async function importDistributiepunten(file: File): Promise<DistributiepuntImportResponse> {
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetchWithRefresh(`${API_BASE_URL}/api/modules/module-2/distributiepunt-import`, {
    method: "POST",
    credentials: "include",
    body: formData,
  });

  if (!response.ok) {
    const errorBody = await response.json().catch(() => null);
    const message = errorBody?.detail ?? `Request failed with status ${response.status}`;
    throw new ApiError(message, response.status);
  }

  return (await response.json()) as DistributiepuntImportResponse;
}

// --- Zone (module-2's "kartracker.zones" lookup screen) ------------------

export function listZones(): Promise<KarTrackerZone[]> {
  return apiFetch<KarTrackerZone[]>("/api/modules/module-2/zones");
}

export function createZone(name: string): Promise<KarTrackerZone> {
  return apiFetch<KarTrackerZone>("/api/modules/module-2/zones", {
    method: "POST",
    body: JSON.stringify({ name }),
  });
}

export function updateZone(zoneId: number, name: string): Promise<KarTrackerZone> {
  return apiFetch<KarTrackerZone>(`/api/modules/module-2/zones/${zoneId}`, {
    method: "PUT",
    body: JSON.stringify({ name }),
  });
}

export function deleteZone(zoneId: number): Promise<void> {
  return apiFetch<void>(`/api/modules/module-2/zones/${zoneId}`, { method: "DELETE" });
}

/** Uploads an XLSX file to bulk-register new zones. Mirrors importKarren above. */
export async function importZones(file: File): Promise<ZoneImportResponse> {
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetchWithRefresh(`${API_BASE_URL}/api/modules/module-2/zone-import`, {
    method: "POST",
    credentials: "include",
    body: formData,
  });

  if (!response.ok) {
    const errorBody = await response.json().catch(() => null);
    const message = errorBody?.detail ?? `Request failed with status ${response.status}`;
    throw new ApiError(message, response.status);
  }

  return (await response.json()) as ZoneImportResponse;
}

// --- Afleverlocatie (module-2's "kartracker.afleverlocaties" master data) ---

export function listAfleverlocaties(): Promise<KarTrackerAfleverlocatie[]> {
  return apiFetch<KarTrackerAfleverlocatie[]>("/api/modules/module-2/afleverlocaties");
}

export function createAfleverlocatie(payload: KarTrackerAfleverlocatieInput): Promise<KarTrackerAfleverlocatie> {
  return apiFetch<KarTrackerAfleverlocatie>("/api/modules/module-2/afleverlocaties", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function updateAfleverlocatie(
  afleverlocatieId: number,
  payload: KarTrackerAfleverlocatieInput,
): Promise<KarTrackerAfleverlocatie> {
  return apiFetch<KarTrackerAfleverlocatie>(`/api/modules/module-2/afleverlocaties/${afleverlocatieId}`, {
    method: "PUT",
    body: JSON.stringify(payload),
  });
}

export function deleteAfleverlocatie(afleverlocatieId: number): Promise<void> {
  return apiFetch<void>(`/api/modules/module-2/afleverlocaties/${afleverlocatieId}`, { method: "DELETE" });
}

/** Uploads an XLSX file to bulk-register new delivery locations. Mirrors importKarren above. */
export async function importAfleverlocaties(file: File): Promise<AfleverlocatieImportResponse> {
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetchWithRefresh(`${API_BASE_URL}/api/modules/module-2/afleverlocatie-import`, {
    method: "POST",
    credentials: "include",
    body: formData,
  });

  if (!response.ok) {
    const errorBody = await response.json().catch(() => null);
    const message = errorBody?.detail ?? `Request failed with status ${response.status}`;
    throw new ApiError(message, response.status);
  }

  return (await response.json()) as AfleverlocatieImportResponse;
}

// --- Intervention Statuses (module-3's "MasterData" lookup screen) ------

export function listInterventionStatuses(): Promise<InterventionStatus[]> {
  return apiFetch<InterventionStatus[]>("/api/modules/module-3/intervention-statuses");
}

export function createInterventionStatus(payload: InterventionStatusInput): Promise<InterventionStatus> {
  return apiFetch<InterventionStatus>("/api/modules/module-3/intervention-statuses", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function updateInterventionStatus(
  statusId: number,
  payload: InterventionStatusInput,
): Promise<InterventionStatus> {
  return apiFetch<InterventionStatus>(`/api/modules/module-3/intervention-statuses/${statusId}`, {
    method: "PUT",
    body: JSON.stringify(payload),
  });
}

export function deleteInterventionStatus(statusId: number): Promise<void> {
  return apiFetch<void>(`/api/modules/module-3/intervention-statuses/${statusId}`, { method: "DELETE" });
}

// --- Intervention Requests (module-3's "Actions" screen) -----------------

/** The MasterData teams for the "Ploeg" dropdown, read via module-3's own
 * lightweight endpoint (not MasterData's) so it works regardless of the
 * user's MasterData role. */
export function listInterventionRequestsTeams(): Promise<InterventionRequestsTeam[]> {
  return apiFetch<InterventionRequestsTeam[]>("/api/modules/module-3/teams");
}

/** Current TeamKar members for the "Team Kar" dropdown, read via module-3's
 * own lightweight endpoint (not TeamKar's admin endpoint) so it works
 * regardless of the user's TeamKar permission. */
export function listTeamKarOptions(): Promise<TeamKarMemberOption[]> {
  return apiFetch<TeamKarMemberOption[]>("/api/modules/module-3/teamkar/options");
}

// --- Intervention Requests (public, no-login form) ------------------------

/** The MasterData teams for the public form's "Ploeg" dropdown — same
 * projection as listInterventionRequestsTeams above, but reachable without
 * being logged in (see app/modules/module_3/public_router.py). */
export function listPublicInterventionRequestTeams(): Promise<InterventionRequestsTeam[]> {
  return apiFetch<InterventionRequestsTeam[]>("/api/public/intervention-requests/teams");
}

/** Submit a customer's intervention request from the public, no-login form. */
export function submitPublicInterventionRequest(
  payload: PublicInterventionRequestInput,
): Promise<InterventionRequest> {
  return apiFetch<InterventionRequest>("/api/public/intervention-requests", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

// --- TeamKar (module-3's fixed-group masterdata screen) -------------------

export function listTeamKarUsers(): Promise<TeamKarUser[]> {
  return apiFetch<TeamKarUser[]>("/api/modules/module-3/teamkar/users");
}

export function setTeamKarMembers(userIds: number[]): Promise<TeamKarUser[]> {
  return apiFetch<TeamKarUser[]>("/api/modules/module-3/teamkar/users", {
    method: "PUT",
    body: JSON.stringify({ user_ids: userIds }),
  });
}

export function listInterventionRequests(): Promise<InterventionRequest[]> {
  return apiFetch<InterventionRequest[]>("/api/modules/module-3/intervention-requests");
}

export function createInterventionRequest(payload: InterventionRequestInput): Promise<InterventionRequest> {
  return apiFetch<InterventionRequest>("/api/modules/module-3/intervention-requests", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function updateInterventionRequest(
  requestId: number,
  payload: InterventionRequestInput,
): Promise<InterventionRequest> {
  return apiFetch<InterventionRequest>(`/api/modules/module-3/intervention-requests/${requestId}`, {
    method: "PUT",
    body: JSON.stringify(payload),
  });
}

export function deleteInterventionRequest(requestId: number): Promise<void> {
  return apiFetch<void>(`/api/modules/module-3/intervention-requests/${requestId}`, { method: "DELETE" });
}
