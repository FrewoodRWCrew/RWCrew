// This file lists the exact "shapes" of data our frontend expects back
// from the FastAPI backend. Keeping them in one place means every
// component that talks to the API agrees on what the data looks like.
// These mirror the Pydantic schemas in the backend (see
// backend/app/schemas/).

/** The three roles a user can hold inside a single module. */
export type ModuleRoleName = "admin" | "editor" | "reader";

/** The currently logged-in user, as returned by GET /api/auth/me. */
export interface CurrentUser {
  id: number;
  email: string;
  display_name: string;
  is_super_admin: boolean;
  language_preference: "nl" | "en";
  /** Every module key (e.g. "module-3") this user is currently allowed to open. */
  accessible_module_keys: string[];
}

/** One module/tile, as returned by GET /api/modules. */
export interface ModuleInfo {
  key: string;
  name: string;
  sort_order: number;
}

/** One user row in the admin "Manage Access" table. */
export interface UserSummary {
  id: number;
  email: string;
  display_name: string;
  is_super_admin: boolean;
  is_active: boolean;
  accessible_module_keys: string[];
}

/** One user's role inside a specific module. */
export interface ModuleRoleAssignment {
  user_id: number;
  email: string;
  display_name: string;
  role: ModuleRoleName | null;
}

/** The placeholder "coming soon" content for one module. */
export interface ModuleStatus {
  module_key: string;
  module_name: string;
  your_role: ModuleRoleName | null;
}

/** One season, as managed on the Master Data screen. */
export interface Season {
  id: number;
  name: string;
}

/** One product, as managed on MasterData's Products screen. */
export interface Product {
  id: number;
  name: string;
  type_id: number | null;
  warehouse_id: number | null;
  warehouse_location: string | null;
  category_id: number | null;
  is_consumable: boolean;
  is_blocked: boolean;
  is_logistics_product: boolean;
  limit_id: number | null;
  description: string | null;
}

/** The fields sent to create or fully update a product. */
export interface ProductInput {
  name: string;
  type_id?: number | null;
  warehouse_id?: number | null;
  warehouse_location?: string | null;
  category_id?: number | null;
  is_consumable?: boolean;
  is_blocked?: boolean;
  is_logistics_product?: boolean;
  limit_id?: number | null;
  description?: string | null;
}

/** One product type, as managed on MasterData's Type screen. */
export interface ProductType {
  id: number;
  name: string;
}

/** One warehouse (Magazijn), as managed on MasterData's Magazijn screen. */
export interface Warehouse {
  id: number;
  name: string;
}

/** One product category (Categorie), as managed on MasterData's Categorie screen. */
export interface ProductCategory {
  id: number;
  name: string;
}

/** One limit option (Limiet), as managed on MasterData's Limiet screen. */
export interface ProductLimit {
  id: number;
  name: string;
}

// --- Tagscan (module-1): custom roles with per-screen permissions ---------

/** One screen registered inside the Tagscan module. */
export interface TagscanScreen {
  id: number;
  key: string;
  label: string;
  sort_order: number;
}

/** One Tagscan role's permissions on one specific screen. */
export interface TagscanScreenPermission {
  screen_id: number;
  screen_key: string;
  screen_label: string;
  can_view: boolean;
  can_create: boolean;
  can_edit: boolean;
  can_delete: boolean;
}

/** One Tagscan role, with its full permission matrix. */
export interface TagscanRole {
  id: number;
  name: string;
  permissions: TagscanScreenPermission[];
}

/** One user with access to Tagscan, and their current role (if any). */
export interface TagscanUserSummary {
  user_id: number;
  email: string;
  display_name: string;
  role_id: number | null;
  role_name: string | null;
}

/** Which Tagscan screens the current user is allowed to view. */
export interface TagscanMyPermissions {
  viewable_screen_keys: string[];
}

/** One folder in the CSV intake directory's tree, with its subfolders nested inside. */
export interface TagscanFolderNode {
  name: string;
  /** Empty string for the root folder; otherwise "/"-separated, relative to the root. */
  path: string;
  children: TagscanFolderNode[];
}

/** One file inside a folder, as shown in the Dashboard screen's file-list pane. */
export interface TagscanFileEntry {
  name: string;
  path: string;
  size_bytes: number;
  modified_at: string;
}

/** One file's text content, for the Dashboard screen's "notepad" preview pane. */
export interface TagscanFileContent {
  path: string;
  content: string;
  truncated: boolean;
}

// --- MasterData (module-9): custom roles with per-screen permissions ------

/** One screen registered inside the MasterData module. */
export interface MasterDataScreen {
  id: number;
  key: string;
  label: string;
  sort_order: number;
}

/** One MasterData role's permissions on one specific screen. */
export interface MasterDataScreenPermission {
  screen_id: number;
  screen_key: string;
  screen_label: string;
  can_view: boolean;
  can_create: boolean;
  can_edit: boolean;
  can_delete: boolean;
}

/** One MasterData role, with its full permission matrix. */
export interface MasterDataRole {
  id: number;
  name: string;
  permissions: MasterDataScreenPermission[];
}

/** One user with access to MasterData, and their current role (if any). */
export interface MasterDataUserSummary {
  user_id: number;
  email: string;
  display_name: string;
  role_id: number | null;
  role_name: string | null;
}

/** Which MasterData screens the current user is allowed to view. */
export interface MasterDataMyPermissions {
  viewable_screen_keys: string[];
}
