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
  AltsienKernlid,
  AltsienKernlidInput,
  DeliveryMethod,
  Festival,
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
  MasterDataDashboardStats,
  MasterDataMyPermissions,
  MasterDataRole,
  MasterDataScreen,
  MasterDataUserSummary,
  Product,
  ProductCategory,
  ProductInput,
  ProductLimit,
  ProductType,
  PublicInterventionRequestInput,
  RfidTag,
  RfidTagImportResponse,
  RfidTagInput,
  Scanner,
  ScannerInput,
  Season,
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
  TagscanUserSummary,
  Team,
  TeamInput,
  TeamKarMemberOption,
  TeamKarUser,
  TeamLocation,
  TeamTask,
  UserSummary,
  Warehouse,
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

// --- Season (module-9's "masterdata.season" screen) ---------------------

export function listSeasons(): Promise<Season[]> {
  return apiFetch<Season[]>("/api/modules/module-9/seasons");
}

export function createSeason(name: string): Promise<Season> {
  return apiFetch<Season>("/api/modules/module-9/seasons", {
    method: "POST",
    body: JSON.stringify({ name }),
  });
}

export function updateSeason(seasonId: number, name: string): Promise<Season> {
  return apiFetch<Season>(`/api/modules/module-9/seasons/${seasonId}`, {
    method: "PUT",
    body: JSON.stringify({ name }),
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

// --- Altsien Kernleden (module-9's "masterdata.altsien-kernleden" screen) ---

export function listAltsienKernleden(): Promise<AltsienKernlid[]> {
  return apiFetch<AltsienKernlid[]>("/api/modules/module-9/altsien-kernleden");
}

export function createAltsienKernlid(payload: AltsienKernlidInput): Promise<AltsienKernlid> {
  return apiFetch<AltsienKernlid>("/api/modules/module-9/altsien-kernleden", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function updateAltsienKernlid(id: number, payload: AltsienKernlidInput): Promise<AltsienKernlid> {
  return apiFetch<AltsienKernlid>(`/api/modules/module-9/altsien-kernleden/${id}`, {
    method: "PUT",
    body: JSON.stringify(payload),
  });
}

export function deleteAltsienKernlid(id: number): Promise<void> {
  return apiFetch<void>(`/api/modules/module-9/altsien-kernleden/${id}`, { method: "DELETE" });
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

/**
 * Uploads a CSV file to bulk-import tags. Uses a plain fetch instead of
 * apiFetch: the body is FormData, not JSON, and the browser must set its
 * own multipart Content-Type (with boundary) — setting it manually would
 * break the upload.
 */
export async function importRfidTags(file: File): Promise<RfidTagImportResponse> {
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetch(`${API_BASE_URL}/api/modules/module-1/tags/import`, {
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
