// Which chapter of Altsien Select's help manual (backend/app/help/content/
// module_8/*.md, the "## [topic | screen]" lines) explains which route —
// used by the "Help bij dit scherm" button in the module layout. A new
// screen gets a chapter there and a line here.

import type { HelpTopicRoute } from "@/components/shared/module-help";

const BASE = "/modules/module-8";

export const ALTSIEN_SELECT_HELP_ROUTES: HelpTopicRoute[] = [
  { path: BASE, topic: "overview", exact: true },
  // The team list and a team's own wizard (/ploeg-wizard/12).
  { path: `${BASE}/ploeg-wizard`, topic: "wizard" },
  { path: `${BASE}/ploegfiche`, topic: "ploegfiche" },
  { path: `${BASE}/requests`, topic: "requests" },
  { path: `${BASE}/request-statuses`, topic: "statuses" },
  { path: `${BASE}/access-rights/roles`, topic: "roles" },
  { path: `${BASE}/access-rights/users`, topic: "users" },
];
