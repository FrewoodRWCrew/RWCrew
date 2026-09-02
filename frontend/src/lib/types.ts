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

/** The fixed, closed set of states an RFID tag can be in. */
export type RfidTagStatus = "active" | "inactive" | "lost" | "damaged" | "retired";

/** One RFID tag, as managed on TagScan's TagManagement screen. */
export interface RfidTag {
  id: number;
  epc_uid: string;
  status: RfidTagStatus;
  assigned_product_id: number | null;
  assigned_serial_number: string | null;
  date_registered: string;
  date_assigned: string | null;
  last_read_at: string | null;
  last_reader_id: string | null;
  last_location: string | null;
  manufacturer: string | null;
  batch_number: string | null;
  notes_1: string | null;
  notes_2: string | null;
  notes_3: string | null;
  notes_4: string | null;
  notes_5: string | null;
}

/** The fields sent to create or fully update an RFID tag. */
export interface RfidTagInput {
  epc_uid: string;
  status?: RfidTagStatus;
  assigned_product_id?: number | null;
  assigned_serial_number?: string | null;
  date_assigned?: string | null;
  last_read_at?: string | null;
  last_reader_id?: string | null;
  last_location?: string | null;
  manufacturer?: string | null;
  batch_number?: string | null;
  notes_1?: string | null;
  notes_2?: string | null;
  notes_3?: string | null;
  notes_4?: string | null;
  notes_5?: string | null;
}

/** What happened to one row of an uploaded CSV import. */
export interface RfidTagImportRowResult {
  row_number: number;
  epc_uid: string | null;
  outcome: "created" | "updated" | "error";
  detail: string | null;
}

/** The full outcome of a CSV import — one result per row, in order. */
export interface RfidTagImportResponse {
  results: RfidTagImportRowResult[];
}

/** How many tags are in one status — one entry per fixed status value. */
export interface TagStatusBreakdownItem {
  status: RfidTagStatus;
  count: number;
}

/** How many tags were registered in one ISO week (Monday start). */
export interface TagWeeklyRegistrationItem {
  week_start: string;
  count: number;
}

/** One product and how many tags are currently assigned to it. */
export interface TagTopProductItem {
  product_name: string;
  tag_count: number;
}

/** Aggregate KPI stats for TagScan's landing dashboard. */
export interface TagDashboardStats {
  total_tags: number;
  active_tags: number;
  assigned_tags: number;
  unassigned_tags: number;
  lost_or_damaged_tags: number;
  registered_this_month: number;
  status_breakdown: TagStatusBreakdownItem[];
  registrations_by_week: TagWeeklyRegistrationItem[];
  top_products: TagTopProductItem[];
}

/** One CSV file logged by the "Tag Headerdata" screen's scan. */
export interface TagHeaderDataEntry {
  id: number;
  filename: string;
  created_at: string;
  line_count: number;
}

/** What happened to one file found in "Unreaded Tags" during a scan. */
export interface TagHeaderDataScanFileResult {
  filename: string;
  outcome: "logged" | "skipped_duplicate" | "error";
  detail: string | null;
}

/** The full outcome of one "Scan" action. */
export interface TagHeaderDataScanResult {
  results: TagHeaderDataScanFileResult[];
  entries: TagHeaderDataEntry[];
}

/** The fixed set of states a scanned CSV line can be in. */
export type TagLineStatus = "converted" | "no_match" | "cancelled";

/** One CSV data line processed by a Tag Headerdata scan, enriched with a
 * snapshot of its matched TagManagement tag (if any).
 */
export interface TagLineDataEntry {
  id: number;
  header_data_id: number;
  header_filename: string;
  line_number: number;
  scanner: string | null;
  epc: string;
  rssi: number | null;
  antenna: number | null;
  count: number | null;
  last_seen: string | null;
  rfid_tag_id: number | null;
  assigned_product_name: string | null;
  assigned_serial_number: string | null;
  manufacturer: string | null;
  batch_number: string | null;
  status: TagLineStatus;
  created_at: string;
}

/** The outcome of one "Synchro" action. */
export interface TagLineDataSyncResult {
  updated_count: number;
  entries: TagLineDataEntry[];
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
