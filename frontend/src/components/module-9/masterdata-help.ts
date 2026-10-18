// Which chapter of MasterData's help manual (backend/app/help/content/
// module_9/*.md, the "## [topic | screen]" lines) explains which route —
// used by the "Help bij dit scherm" button in the module layout. A new
// screen gets a chapter there and a line here.

import type { HelpTopicRoute } from "@/components/shared/module-help";

const BASE = "/modules/module-9";

export const MASTERDATA_HELP_ROUTES: HelpTopicRoute[] = [
  { path: BASE, topic: "overview", exact: true },
  { path: `${BASE}/season`, topic: "season" },
  { path: `${BASE}/festival`, topic: "festival" },
  // /teams itself; its sub-screens below win because they're more specific.
  { path: `${BASE}/teams`, topic: "teams" },
  { path: `${BASE}/teams/responsibles`, topic: "team-responsibles" },
  { path: `${BASE}/teams/location`, topic: "team-location" },
  { path: `${BASE}/teams/delivery-method`, topic: "delivery-method" },
  { path: `${BASE}/teams/tasks`, topic: "team-tasks" },
  // /products itself; same rule for its sub-screens.
  { path: `${BASE}/products`, topic: "products" },
  { path: `${BASE}/products/types`, topic: "product-types" },
  { path: `${BASE}/products/warehouses`, topic: "warehouses" },
  { path: `${BASE}/products/categories`, topic: "product-categories" },
  { path: `${BASE}/products/limits`, topic: "product-limits" },
  { path: `${BASE}/data-upload-download`, topic: "data-upload" },
  { path: `${BASE}/access-rights/roles`, topic: "roles" },
  { path: `${BASE}/access-rights/users`, topic: "users" },
];
