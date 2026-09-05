// MasterData's landing page: the first screen shown when the module is
// opened — a KPI dashboard ("Masterdata Overview", stat tiles + charts)
// built from /api/modules/module-9/dashboard, the same treatment
// TagScan's own module-1/page.tsx gives its dashboard. Season (the
// module's other actual piece of master data) has its own sidebar link,
// see modules/module-9/season/page.tsx. No 403 handling needed here
// beyond what the module's own layout.tsx already does (it checks module
// access and 403s before this ever renders) — the dashboard endpoint is
// gated the same unconditional way.

import { serverApiFetch } from "@/lib/server-api";
import type { MasterDataDashboardStats } from "@/lib/types";
import { MasterDataDashboard } from "@/components/module-9/masterdata-dashboard";

export default async function MasterDataLandingPage() {
  const stats = await serverApiFetch<MasterDataDashboardStats>("/api/modules/module-9/dashboard");

  return <MasterDataDashboard stats={stats} />;
}
