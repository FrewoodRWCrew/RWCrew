// Which chapter of Walkies's help manual (backend/app/help/content/
// module_6/*.md, the "## [topic | screen]" lines) explains which route —
// used by the "Help bij dit scherm" button in the module layout. A new
// screen gets a chapter there and a line here.

import type { HelpTopicRoute } from "@/components/shared/module-help";

const BASE = "/modules/module-6";

export const WALKIES_HELP_ROUTES: HelpTopicRoute[] = [
  { path: BASE, topic: "overview", exact: true },
  { path: `${BASE}/access-rights/roles`, topic: "roles" },
  { path: `${BASE}/access-rights/users`, topic: "users" },
];
