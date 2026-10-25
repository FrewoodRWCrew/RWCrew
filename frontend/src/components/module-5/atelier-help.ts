// Which chapter of Atelier's help manual (backend/app/help/content/
// module_5/*.md, the "## [topic | screen]" lines) explains which route —
// used by the "Help bij dit scherm" button in the module layout. A new
// screen gets a chapter there and a line here.

import type { HelpTopicRoute } from "@/components/shared/module-help";

const BASE = "/modules/module-5";

export const ATELIER_HELP_ROUTES: HelpTopicRoute[] = [
  { path: BASE, topic: "overview", exact: true },
  { path: `${BASE}/desk`, topic: "desk", exact: true },
  { path: `${BASE}/desk/open`, topic: "open" },
  { path: `${BASE}/reservations`, topic: "reservations" },
  { path: `${BASE}/reservations/preparation`, topic: "preparation" },
  { path: `${BASE}/stock`, topic: "stock", exact: true },
  { path: `${BASE}/stock/receipt`, topic: "receipt" },
  { path: `${BASE}/stock/wash`, topic: "wash" },
  { path: `${BASE}/stock/write-off`, topic: "writeoff" },
  { path: `${BASE}/stock/count`, topic: "count" },
  { path: `${BASE}/stock/bookings`, topic: "bookings" },
  { path: `${BASE}/stock/order-needs`, topic: "orderneeds" },
  { path: `${BASE}/masterdata/articles/sizes`, topic: "sizes" },
  { path: `${BASE}/masterdata/articles`, topic: "articles" },
  { path: `${BASE}/masterdata/data-upload-download`, topic: "dataupload" },
  { path: `${BASE}/settings`, topic: "settings", exact: true },
  { path: `${BASE}/settings/scan-test`, topic: "scantest" },
  { path: `${BASE}/access-rights/roles`, topic: "roles" },
  { path: `${BASE}/access-rights/users`, topic: "users" },
];
