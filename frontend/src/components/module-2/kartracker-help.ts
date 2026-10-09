// Which chapter of KarTracker's help manual (backend/app/help/content/
// module_2/*.md, the "## [topic | screen]" lines) explains which route —
// used by the "Help bij dit scherm" button in the module layout. A new
// screen gets a chapter there and a line here.

import type { HelpTopicRoute } from "@/components/shared/module-help";

const BASE = "/modules/module-2";

export const KARTRACKER_HELP_ROUTES: HelpTopicRoute[] = [
  { path: BASE, topic: "overview", exact: true },
  // "Manuele kar beweging"; the screens under /actions/... win because
  // they're more specific.
  { path: `${BASE}/actions`, topic: "movement" },
  { path: `${BASE}/actions/kar-planning`, topic: "kar-planning" },
  { path: `${BASE}/actions/kar-map`, topic: "kar-map" },
  { path: `${BASE}/actions/plan-kar`, topic: "plan-kar" },
  { path: `${BASE}/kar-management`, topic: "kar-management" },
  { path: `${BASE}/distributiepunten`, topic: "distributiepunten" },
  { path: `${BASE}/zones`, topic: "zones" },
  { path: `${BASE}/afleverlocaties`, topic: "afleverlocaties" },
  { path: `${BASE}/kar-statuses`, topic: "kar-statuses" },
  { path: `${BASE}/delivery-dates`, topic: "delivery-dates" },
  { path: `${BASE}/data-upload-download`, topic: "data-upload" },
  { path: `${BASE}/groundplan`, topic: "groundplan" },
  { path: `${BASE}/access-rights/roles`, topic: "roles" },
  { path: `${BASE}/access-rights/users`, topic: "users" },
];
