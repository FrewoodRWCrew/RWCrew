// Which chapter of TagScan's help manual (backend/app/help/content/
// module_1/*.md, the "## [topic | screen]" lines) explains which route —
// used by the "Help bij dit scherm" button in the module layout. A new
// screen gets a chapter there and a line here. (The waiting-actions dialog
// links its own "pending" topic, see pending-actions-dialog.tsx.)

import type { HelpTopicRoute } from "@/components/shared/module-help";

const BASE = "/modules/module-1";

export const TAGSCAN_HELP_ROUTES: HelpTopicRoute[] = [
  { path: BASE, topic: "overview", exact: true },
  { path: `${BASE}/files`, topic: "files" },
  { path: `${BASE}/tag-headerdata`, topic: "header-data" },
  { path: `${BASE}/tag-linedata`, topic: "line-data" },
  { path: `${BASE}/tag-management`, topic: "tag-management" },
  { path: `${BASE}/scanners`, topic: "scanners" },
  { path: `${BASE}/data-upload-download`, topic: "data-upload" },
  { path: `${BASE}/access-rights/roles`, topic: "roles" },
  { path: `${BASE}/access-rights/users`, topic: "users" },
  { path: `${BASE}/settings`, topic: "settings" },
];
