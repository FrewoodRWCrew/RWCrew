// Friendly names for the data shapes the backend sends and expects. They
// come straight from the generated API contract (src/api/generated/), so
// they can never drift from what the backend really serves — regenerate
// with "npm run gen:api" after the backend's phone API changes.

import type { components } from "../api/generated/schema";

type Schemas = components["schemas"];

export type CurrentUser = Schemas["CurrentUserResponse"];
export type ModuleInfo = Schemas["ModuleResponse"];

export type InterventionRequest = Schemas["InterventionRequestResponse"];
// What is sent to create or update a request (the number and timestamp are
// set by the backend, never by the app).
export type InterventionRequestInput = Schemas["InterventionRequestCreateRequest"];
export type InterventionStatus = Schemas["InterventionStatusResponse"];
export type Dashboard = Schemas["InterventionRequestsDashboardResponse"];
export type Lookups = Schemas["MobileModule3LookupsResponse"];
export type Module3Permissions = Schemas["MobileModule3PermissionsResponse"];

// KarTracker's KarScan (module-2).
export type Module2Permissions = Schemas["MobileModule2PermissionsResponse"];
// The kar found for a scanned QR code, plus its last few movements.
export type KarScan = Schemas["MobileKarScanResponse"];
export type KarStatusOption = Schemas["PlanKarOption"];
export type KarAction = Schemas["KarActionResponse"];
// What is sent to log a movement (team and timestamp are set by the backend).
export type KarActionInput = Schemas["KarActionCreateRequest"];
export type Season = Schemas["MobileSeasonResponse"];
export type KarPlanningReport = Schemas["KarPlanningReportResponse"];
export type KarPlanningRow = Schemas["KarPlanningResponse"];
export type KarMapData = Schemas["KarMapResponse"];
export type Groundplan = Schemas["KarTrackerGroundplanResponse"];
