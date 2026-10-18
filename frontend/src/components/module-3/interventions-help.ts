// Which chapter of Interventies' help manual (backend/app/help/content/
// module_3/*.md, the "## [topic | screen]" lines) explains which route —
// used by the "Help bij dit scherm" button in the module layout. A new
// screen gets a chapter there and a line here.

import type { HelpTopicRoute } from "@/components/shared/module-help";

const BASE = "/modules/module-3";

export const INTERVENTIONS_HELP_ROUTES: HelpTopicRoute[] = [
  { path: BASE, topic: "overview", exact: true },
  { path: `${BASE}/intervention-requests`, topic: "requests" },
  { path: `${BASE}/intervention-statuses`, topic: "statuses" },
  { path: `${BASE}/teamkar`, topic: "teamkar" },
  { path: `${BASE}/settings/mailing-list`, topic: "mailing-list" },
  { path: `${BASE}/access-rights/roles`, topic: "roles" },
  { path: `${BASE}/access-rights/users`, topic: "users" },
];
