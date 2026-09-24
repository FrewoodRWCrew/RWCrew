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
