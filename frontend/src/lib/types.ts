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
  is_altsien_kernlid: boolean;
  phone: string | null;
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
  periode_open: boolean;
}

/** The fields sent to create or fully update a season. */
export interface SeasonInput {
  name: string;
  periode_open: boolean;
}

/** One team location, as managed on MasterData's Team Location screen (nested under Teams). */
export interface TeamLocation {
  id: number;
  location: string;
}

/** One delivery method, as managed on MasterData's Delivery Method screen (nested under Teams). */
export interface DeliveryMethod {
  id: number;
  delivery_method: string;
}

/** One team task, as managed on MasterData's Team Tasks screen (nested under Teams). */
export interface TeamTask {
  id: number;
  team_tasks: string;
}

/** One festival, as managed on MasterData's Festivals screen. */
export interface Festival {
  id: number;
  name: string;
  start_date: string;
  end_date: string;
  season_id: number;
  active: boolean;
}

/** The fields sent to create or fully update a festival. */
export interface FestivalInput {
  name: string;
  start_date: string;
  end_date: string;
  season_id: number;
  active: boolean;
}

/** One user flagged "Altsien Kernlid" (set on the Manage Access screen), as
 * offered in the Teams / Distributiepunt / Afleverlocatie pickers. */
export interface AltsienKernlid {
  id: number;
  display_name: string;
  email: string;
  phone: string | null;
}

/** One team, as managed on MasterData's Teams screen. task_ids/kernlid_ids
 * reference Team Task rows / users flagged Altsien Kernlid (many-to-many). */
export interface Team {
  id: number;
  name: string;
  location_id: number | null;
  delivery_method_id: number | null;
  task_ids: number[];
  kernlid_ids: number[];
  description: string | null;
  active: boolean;
}

/** The fields sent to create or fully update a team. */
export interface TeamInput {
  name: string;
  location_id?: number | null;
  delivery_method_id?: number | null;
  task_ids?: number[];
  kernlid_ids?: number[];
  description?: string | null;
  active?: boolean;
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

/** The fixed, closed set of reader hardware a scanner device can be. */
export type ScannerTechnology = "Raspberry Pi 3" | "Raspberry Pi 4" | "Raspberry Pi 5" | "Other";

/** One registered scanner device, as managed on TagScan's Scanners screen. */
export interface Scanner {
  id: number;
  scanner: string;
  type_id: number;
  technology: ScannerTechnology;
  location: string | null;
  description: string | null;
  info1: string | null;
  info2: string | null;
  info3: string | null;
  /** Whether an API key currently exists for this scanner's CSV device-intake uploads. */
  has_api_key: boolean;
  api_key_last_used_at: string | null;
}

/** The brand-new plaintext API key for a scanner, returned exactly once
 * at generation time — see POST /api/modules/module-1/scanners/{id}/api-key. */
export interface ScannerApiKey {
  api_key: string;
}

/** TagScan's module-wide settings, as shown on the Settings screen. */
export interface TagscanSettings {
  receive_folder_path: string;
  /** Whether receive_folder_path is a DB-saved override, or just the
   * backend's .env-configured default shown because nothing's been saved yet. */
  is_override: boolean;
}

/** The fields sent to create or fully update a scanner device. Unlike
 * Product's type_id, a scanner's type is always required (see
 * backend/app/db/models/scanner.py) — nullability only exists transiently
 * in the "Scanners" screen's own form state, not on this wire type. */
export interface ScannerInput {
  scanner: string;
  type_id: number;
  technology: ScannerTechnology;
  location?: string | null;
  description?: string | null;
  info1?: string | null;
  info2?: string | null;
  info3?: string | null;
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
  unreaded_tags_count: number;
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
  // The raw "Scanner" CSV value, and — when it matches a registered
  // Scanners device by name — a snapshot of that device's key fields.
  scanner: string | null;
  scanner_id: number | null;
  scanner_name: string | null;
  scanner_location: string | null;
  scanner_technology: string | null;
  // The file's "Mode" and "Action" CSV values (first non-empty per file).
  mode: string | null;
  action: string | null;
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
  // The line's own "Mode"/"Action" CSV value, or its file's header value.
  mode: string | null;
  action: string | null;
  rfid_tag_id: number | null;
  assigned_product_name: string | null;
  assigned_serial_number: string | null;
  manufacturer: string | null;
  batch_number: string | null;
  // Which registered Scanners device the raw "scanner" text matched, if
  // any — null means no match was found (soft match).
  scanner_id: number | null;
  scanner_name: string | null;
  scanner_location: string | null;
  scanner_technology: string | null;
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

/** Which MasterData screens the current user is allowed to view, and on
 * which of those they're also allowed to create. */
export interface MasterDataMyPermissions {
  viewable_screen_keys: string[];
  creatable_screen_keys: string[];
}

/** How many products have one product type — plus a trailing entry with
 * type_name null for products with no type set ("Unassigned"). */
export interface MasterDataTypeBreakdownItem {
  type_name: string | null;
  count: number;
}

/** Same as MasterDataTypeBreakdownItem, but for product categories. */
export interface MasterDataCategoryBreakdownItem {
  category_name: string | null;
  count: number;
}

/** Same as MasterDataTypeBreakdownItem, but for warehouses. */
export interface MasterDataWarehouseBreakdownItem {
  warehouse_name: string | null;
  count: number;
}

/** Aggregate KPI stats for MasterData's landing dashboard ("Masterdata Overview"). */
export interface MasterDataDashboardStats {
  total_products: number;
  total_seasons: number;
  blocked_products: number;
  consumable_products: number;
  logistics_products: number;
  products_missing_classification: number;
  products_by_type: MasterDataTypeBreakdownItem[];
  products_by_category: MasterDataCategoryBreakdownItem[];
  products_by_warehouse: MasterDataWarehouseBreakdownItem[];
}

/** One status, as managed on module-3's Intervention Statuses screen. */
export interface InterventionStatus {
  id: number;
  name: string;
  is_open: boolean;
  color: string;
}

/** The fields sent to create or fully update a status. */
export interface InterventionStatusInput {
  name: string;
  is_open: boolean;
  color: string;
}

/** One MasterData team, as shown in the Intervention Requests screen's
 * "Ploeg" dropdown — read via module-3's own lightweight "/teams"
 * endpoint (see api.ts's listInterventionRequestsTeams), not MasterData's
 * own Team type, so it works regardless of the user's MasterData role. */
export interface InterventionRequestsTeam {
  id: number;
  name: string;
}

/** One intervention request, as shown on module-3's Intervention Requests screen.
 * Exactly one of team_id/team_name is ever set — team_name carries a Ploeg
 * name typed on the public form that isn't a real MasterData team yet. */
export interface InterventionRequest {
  id: number;
  request_number: string;
  submitted_at: string;
  team_id: number | null;
  team_name: string | null;
  cart_number: string | null;
  question: string;
  employee_name: string | null;
  employee_phone: string | null;
  preferred_delivery_at: string | null;
  delivery_location: string | null;
  zone: string | null;
  status_id: number;
  handled_by: string | null;
  team_cart_user_id: number | null;
}

/** The fields sent to create or fully update an intervention request
 * (the staff-only admin dialog — see PublicInterventionRequestInput for the
 * public form's trimmed-down equivalent). */
export interface InterventionRequestInput {
  team_id: number | null;
  team_name?: string | null;
  cart_number?: string | null;
  question: string;
  employee_name?: string | null;
  employee_phone?: string | null;
  preferred_delivery_at?: string | null;
  delivery_location?: string | null;
  zone?: string | null;
  status_id: number;
  handled_by?: string | null;
  team_cart_user_id?: number | null;
}

/** The fields the public (no-login) intervention-request form sends —
 * status_id/handled_by/team_cart_user_id are internal-only and set by the
 * backend itself, so they're deliberately absent here. */
export interface PublicInterventionRequestInput {
  team_id: number | null;
  team_name?: string | null;
  cart_number?: string | null;
  question: string;
  employee_name?: string | null;
  employee_phone?: string | null;
  preferred_delivery_at?: string | null;
  delivery_location?: string | null;
  zone?: string | null;
}

/** One status, with how many intervention requests currently carry it —
 * one bar of the KPI dashboard's status breakdown chart. */
export interface InterventionRequestsStatusBreakdownItem {
  status_name: string;
  color: string;
  count: number;
}

/** One team/association name, with how many intervention requests were
 * logged for it — one bar of the KPI dashboard's team breakdown chart. */
export interface InterventionRequestsTeamBreakdownItem {
  team_name: string;
  count: number;
}

/** Aggregate KPI stats for Intervention Requests' landing dashboard ("KPI overview"). */
export interface InterventionRequestsDashboardStats {
  total_requests: number;
  open_requests: number;
  closed_requests: number;
  status_breakdown: InterventionRequestsStatusBreakdownItem[];
  team_breakdown: InterventionRequestsTeamBreakdownItem[];
}

/** One app user, with whether they're currently a member of TeamKar — one
 * row of module-3's TeamKar screen's table. */
export interface TeamKarUser {
  user_id: number;
  email: string;
  display_name: string;
  is_member: boolean;
}

/** One current TeamKar member, as shown in the Intervention Requests
 * screen's "Team Kar" dropdown — read via module-3's own lightweight
 * "/teamkar/options" endpoint, gated by the requests screen's own
 * permission rather than TeamKar's own admin permission. */
export interface TeamKarMemberOption {
  id: number;
  display_name: string;
}

// --- Intervention Requests (module-3): custom roles with per-screen permissions ---

/** One screen registered inside the Intervention Requests module. */
export interface InterventionRequestsScreen {
  id: number;
  key: string;
  label: string;
  sort_order: number;
}

/** One Intervention Requests role's permissions on one specific screen. */
export interface InterventionRequestsScreenPermission {
  screen_id: number;
  screen_key: string;
  screen_label: string;
  can_view: boolean;
  can_create: boolean;
  can_edit: boolean;
  can_delete: boolean;
}

/** One Intervention Requests role, with its full permission matrix. */
export interface InterventionRequestsRole {
  id: number;
  name: string;
  permissions: InterventionRequestsScreenPermission[];
}

/** One user with access to Intervention Requests, and their current role (if any). */
export interface InterventionRequestsUserSummary {
  user_id: number;
  email: string;
  display_name: string;
  role_id: number | null;
  role_name: string | null;
}

/** Which Intervention Requests screens the current user is allowed to view. */
export interface InterventionRequestsMyPermissions {
  viewable_screen_keys: string[];
}

// --- KarTracker (module-2): custom roles with per-screen permissions ---
//
// The Access Rights scaffold (Roles + Users), plus the Karlijst phase's
// KarStatussen lookup and KarManagement fleet registry. Delivery planning
// types get added here once that phase is designed.

/** One screen registered inside the KarTracker module. */
export interface KarTrackerScreen {
  id: number;
  key: string;
  label: string;
  sort_order: number;
}

/** One KarTracker role's permissions on one specific screen. */
export interface KarTrackerScreenPermission {
  screen_id: number;
  screen_key: string;
  screen_label: string;
  can_view: boolean;
  can_create: boolean;
  can_edit: boolean;
  can_delete: boolean;
}

/** One KarTracker role, with its full permission matrix. */
export interface KarTrackerRole {
  id: number;
  name: string;
  permissions: KarTrackerScreenPermission[];
}

/** One user with access to KarTracker, and their current role (if any). */
export interface KarTrackerUserSummary {
  user_id: number;
  email: string;
  display_name: string;
  role_id: number | null;
  role_name: string | null;
}

/** Which KarTracker screens the current user is allowed to view, and on
 * which of those they're also allowed to create. */
export interface KarTrackerMyPermissions {
  viewable_screen_keys: string[];
  creatable_screen_keys: string[];
  editable_screen_keys: string[];
}

/** One status a kar can be in, as managed on the KarStatussen screen. */
export interface KarTrackerKarStatus {
  id: number;
  name: string;
}

/** One kar, as shown on the KarManagement screen. */
export interface KarTrackerKar {
  id: number;
  kar_nummer: string;
  status_id: number;
  team_id: number | null;
  transport_type_id: number;
  last_latitude: number | null;
  last_longitude: number | null;
  last_recorded_at: string | null;
}

/** What's sent to create or update a kar. */
export interface KarTrackerKarInput {
  kar_nummer: string;
  status_id: number;
  team_id: number | null;
  transport_type_id: number;
  last_latitude: number | null;
  last_longitude: number | null;
  last_recorded_at: string | null;
}

/** One row of the read-only Kar Planning report (joined KarManagement + lookups). */
export interface KarTrackerKarPlanningRow {
  id: number;
  kar_nummer: string;
  status_name: string;
  team_name: string | null;
  transport_type_name: string;
  /** Festival id -> planned afleverlocatie name; festivals with none planned are absent. */
  afleverlocaties: Record<number, string>;
  geolocation: string | null;
}

/** One festival column of the Kar Planning report. */
export interface KarTrackerKarPlanningFestival {
  id: number;
  name: string;
}

/** The Kar Planning report: the requested season's active festivals plus one row per kar. */
export interface KarTrackerKarPlanningReport {
  festivals: KarTrackerKarPlanningFestival[];
  rows: KarTrackerKarPlanningRow[];
}

/** One kar's pin/list entry on the Kar Map screen. */
export interface KarTrackerKarMapKarRow {
  id: number;
  kar_nummer: string;
  status_name: string;
  team_name: string | null;
  latitude: number | null;
  longitude: number | null;
}

/** One delivery location's pin/list entry on the Kar Map screen. */
export interface KarTrackerKarMapAfleverlocatieRow {
  id: number;
  name: string;
  description: string | null;
  zone_name: string;
  distributiepunt_name: string;
  latitude: number | null;
  longitude: number | null;
}

/** One distribution point's pin/list entry on the Kar Map screen. */
export interface KarTrackerKarMapDistributiepuntRow {
  id: number;
  name: string;
  terrein_positie: string | null;
  latitude: number | null;
  longitude: number | null;
}

/** The full Kar Map payload: one array per layer (Karren/Afleverlocaties/
 * Distributiepunten). Rows with null latitude/longitude are included —
 * excluded from the map, shown in the side list instead. */
export interface KarTrackerKarMapResponse {
  karren: KarTrackerKarMapKarRow[];
  afleverlocaties: KarTrackerKarMapAfleverlocatieRow[];
  distributiepunten: KarTrackerKarMapDistributiepuntRow[];
}

/** The event site's ground-plan overlay: whether an image has ever been
 * uploaded, and its south-west/north-east corner coordinates (all null
 * until first configured on the Grondplan screen). */
export interface KarTrackerGroundplan {
  has_image: boolean;
  sw_latitude: number | null;
  sw_longitude: number | null;
  ne_latitude: number | null;
  ne_longitude: number | null;
}

/**
 * What happened to one row of an uploaded bulk kar-import workbook. Unlike
 * TagScan's tag import, there is no "updated" outcome — a kar_nummer that
 * already exists is rejected as an error instead of being upserted.
 */
export interface KarImportRowResult {
  row_number: number;
  kar_nummer: string | null;
  outcome: "created" | "error";
  detail: string | null;
}

/** The full outcome of a bulk kar import — one result per row, in order. */
export interface KarImportResponse {
  results: KarImportRowResult[];
}

/**
 * What happened to one row of an uploaded bulk kar-status import. A name
 * that already exists is rejected as an error instead of being upserted —
 * same rule as the Karren import.
 */
export interface KarStatusImportRowResult {
  row_number: number;
  name: string | null;
  outcome: "created" | "error";
  detail: string | null;
}

/** The full outcome of a bulk kar-status import — one result per row, in order. */
export interface KarStatusImportResponse {
  results: KarStatusImportRowResult[];
}

/** One distribution point, as shown on the Distributiepunten screen. */
export interface KarTrackerDistributiepunt {
  id: number;
  name: string;
  latitude: number | null;
  longitude: number | null;
  terrein_positie: string | null;
  altsien_kernlid_id: number | null;
}

/** What's sent to create or update a distribution point. */
export interface KarTrackerDistributiepuntInput {
  name: string;
  latitude: number | null;
  longitude: number | null;
  terrein_positie: string | null;
  altsien_kernlid_id: number | null;
}

/**
 * What happened to one row of an uploaded bulk distributiepunt-import
 * workbook. A name that already exists is rejected as an error instead of
 * being upserted — same rule as the Karren import.
 */
export interface DistributiepuntImportRowResult {
  row_number: number;
  name: string | null;
  outcome: "created" | "error";
  detail: string | null;
}

/** The full outcome of a bulk distributiepunt import — one result per row, in order. */
export interface DistributiepuntImportResponse {
  results: DistributiepuntImportRowResult[];
}

/** One delivery zone, as managed on the Zone screen. */
export interface KarTrackerZone {
  id: number;
  name: string;
}

/**
 * What happened to one row of an uploaded bulk zone-import workbook. A
 * name that already exists is rejected as an error instead of being
 * upserted.
 */
export interface ZoneImportRowResult {
  row_number: number;
  name: string | null;
  outcome: "created" | "error";
  detail: string | null;
}

/** The full outcome of a bulk zone import — one result per row, in order. */
export interface ZoneImportResponse {
  results: ZoneImportRowResult[];
}

/** One delivery location, as shown on the Afleverlocatie screen. */
export interface KarTrackerAfleverlocatie {
  id: number;
  name: string;
  description: string | null;
  zone_id: number;
  distributiepunt_id: number;
  latitude: number | null;
  longitude: number | null;
  terrein_positie: string | null;
  altsien_kernlid_id: number | null;
  active: boolean;
}

/** What's sent to create or update a delivery location. */
export interface KarTrackerAfleverlocatieInput {
  name: string;
  description: string | null;
  zone_id: number;
  distributiepunt_id: number;
  latitude: number | null;
  longitude: number | null;
  terrein_positie: string | null;
  altsien_kernlid_id: number | null;
  active: boolean;
}

/** One entry of a "Plan a kar" dropdown (a team or a delivery location). */
export interface KarTrackerPlanKarOption {
  id: number;
  name: string;
}

/** A "Plan a kar" delivery-location dropdown entry: name plus description, shown next to it. */
export interface KarTrackerPlanKarAfleverlocatieOption extends KarTrackerPlanKarOption {
  description: string | null;
}

/** One "Plan a kar" matrix row: a festival plus its saved delivery location, if any. */
export interface KarTrackerPlanKarRow {
  festival_id: number;
  festival_name: string;
  afleverlocatie_id: number | null;
}

/** The "Plan a kar" matrix for one team in one season. */
export interface KarTrackerPlanKar {
  season_id: number;
  team_id: number;
  rows: KarTrackerPlanKarRow[];
}

/** What the "Plan a kar" Save button sends. A null afleverlocatie_id clears that festival's assignment. */
export interface KarTrackerPlanKarSaveInput {
  season_id: number;
  team_id: number;
  rows: { festival_id: number; afleverlocatie_id: number | null }[];
}

/** One "Delivery Dates" row: a festival plus its saved delivery/pick-up dates (ISO YYYY-MM-DD), if any. */
export interface KarTrackerLeverdatumRow {
  festival_id: number;
  festival_name: string;
  delivery_date: string | null;
  pickup_date: string | null;
}

/** The "Delivery Dates" table for one season. */
export interface KarTrackerLeverdatum {
  season_id: number;
  rows: KarTrackerLeverdatumRow[];
}

/** What the "Delivery Dates" Save button sends. A row with both dates null clears that festival's record. */
export interface KarTrackerLeverdatumSaveInput {
  season_id: number;
  rows: { festival_id: number; delivery_date: string | null; pickup_date: string | null }[];
}

/**
 * What happened to one row of an uploaded bulk afleverlocatie-import
 * workbook. A name that already exists is rejected as an error instead of
 * being upserted — same rule as the Karren import.
 */
export interface AfleverlocatieImportRowResult {
  row_number: number;
  name: string | null;
  outcome: "created" | "error";
  detail: string | null;
}

/** The full outcome of a bulk afleverlocatie import — one result per row, in order. */
export interface AfleverlocatieImportResponse {
  results: AfleverlocatieImportRowResult[];
}

// --- MasterData Data Upload/Download: one row-result pair per table, all
// without an "updated" outcome — a row naming something that already
// exists is rejected as an error instead of being upserted (except
// Product/Festival, which have no uniqueness rule at all). ------------------

export interface SeasonImportRowResult {
  row_number: number;
  name: string | null;
  outcome: "created" | "error";
  detail: string | null;
}

export interface SeasonImportResponse {
  results: SeasonImportRowResult[];
}

export interface ProductTypeImportRowResult {
  row_number: number;
  name: string | null;
  outcome: "created" | "error";
  detail: string | null;
}

export interface ProductTypeImportResponse {
  results: ProductTypeImportRowResult[];
}

export interface WarehouseImportRowResult {
  row_number: number;
  name: string | null;
  outcome: "created" | "error";
  detail: string | null;
}

export interface WarehouseImportResponse {
  results: WarehouseImportRowResult[];
}

export interface ProductCategoryImportRowResult {
  row_number: number;
  name: string | null;
  outcome: "created" | "error";
  detail: string | null;
}

export interface ProductCategoryImportResponse {
  results: ProductCategoryImportRowResult[];
}

export interface ProductLimitImportRowResult {
  row_number: number;
  name: string | null;
  outcome: "created" | "error";
  detail: string | null;
}

export interface ProductLimitImportResponse {
  results: ProductLimitImportRowResult[];
}

export interface TeamLocationImportRowResult {
  row_number: number;
  location: string | null;
  outcome: "created" | "error";
  detail: string | null;
}

export interface TeamLocationImportResponse {
  results: TeamLocationImportRowResult[];
}

export interface DeliveryMethodImportRowResult {
  row_number: number;
  delivery_method: string | null;
  outcome: "created" | "error";
  detail: string | null;
}

export interface DeliveryMethodImportResponse {
  results: DeliveryMethodImportRowResult[];
}

export interface TeamTaskImportRowResult {
  row_number: number;
  team_tasks: string | null;
  outcome: "created" | "error";
  detail: string | null;
}

export interface TeamTaskImportResponse {
  results: TeamTaskImportRowResult[];
}

export interface FestivalImportRowResult {
  row_number: number;
  name: string | null;
  outcome: "created" | "error";
  detail: string | null;
}

export interface FestivalImportResponse {
  results: FestivalImportRowResult[];
}

export interface ProductImportRowResult {
  row_number: number;
  name: string | null;
  outcome: "created" | "error";
  detail: string | null;
}

export interface ProductImportResponse {
  results: ProductImportRowResult[];
}

/** Team's bulk import only covers its scalar fields — task/kernlid links
 * are not part of this bulk tool, see team_import.py on the backend. */
export interface TeamImportRowResult {
  row_number: number;
  name: string | null;
  outcome: "created" | "error";
  detail: string | null;
}

export interface TeamImportResponse {
  results: TeamImportRowResult[];
}

// --- Login History (Toegangsbeheer) ----------------------------------

/** One login attempt (successful or not), as shown on the admin "Login
 * History" screen. */
export interface LoginHistoryEntry {
  id: number;
  user_id: number | null;
  email_attempted: string;
  /** Null when user_id is null (unknown email, or the matched user has
   * since been deleted). */
  display_name: string | null;
  success: boolean;
  ip_address: string | null;
  created_at: string;
}

/** One page of login history, plus the total row count for pagination. */
export interface LoginHistoryPage {
  items: LoginHistoryEntry[];
  total: number;
}
