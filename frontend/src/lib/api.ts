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
  MasterDataMyPermissions,
  MasterDataRole,
  MasterDataScreen,
  MasterDataUserSummary,
  Product,
  ProductCategory,
  ProductInput,
  ProductLimit,
  ProductType,
  Season,
  TagscanFileContent,
  TagscanFileEntry,
  TagscanFolderNode,
  TagscanMyPermissions,
  TagscanRole,
  TagscanScreen,
  TagscanUserSummary,
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

// --- MasterData (module-9) -------------------------------------------------

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
