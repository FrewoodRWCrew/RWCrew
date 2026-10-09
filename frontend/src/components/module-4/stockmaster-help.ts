// Which chapter of StockMaster's help manual (backend/app/help/content/
// module_4/*.md, the "## [topic | screen]" lines) explains which route —
// used by the "Help bij dit scherm" button in the module layout. A new
// screen gets a chapter there and a line here.

import type { HelpTopicRoute } from "@/components/shared/module-help";
import { STOCKMASTER_BASE } from "@/components/module-4/stockmaster-common";

const BASE = STOCKMASTER_BASE;

export const STOCKMASTER_HELP_ROUTES: HelpTopicRoute[] = [
  { path: BASE, topic: "kpi", exact: true },
  { path: `${BASE}/stock`, topic: "stock" },
  // /kars and a kar's detail page (/kars/12); the kar actions below win
  // because they're more specific.
  { path: `${BASE}/kars`, topic: "kars" },
  { path: `${BASE}/book-in`, topic: "book-in" },
  { path: `${BASE}/kars/load`, topic: "kar-load" },
  { path: `${BASE}/book-out`, topic: "book-out" },
  { path: `${BASE}/kars/dispatch`, topic: "kar-dispatch" },
  { path: `${BASE}/kars/return`, topic: "kar-return" },
  { path: `${BASE}/kars/unload`, topic: "kar-unload" },
  { path: `${BASE}/count`, topic: "count" },
  { path: `${BASE}/requirements`, topic: "requirements" },
  { path: `${BASE}/order-needs`, topic: "order-needs" },
  { path: `${BASE}/bookings`, topic: "bookings" },
  { path: `${BASE}/settings`, topic: "reasons" },
  { path: `${BASE}/access-rights/roles`, topic: "roles" },
  { path: `${BASE}/access-rights/users`, topic: "users" },
];
