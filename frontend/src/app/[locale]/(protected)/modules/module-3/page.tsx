// Intervention Requests' landing page: the first screen shown when the
// module is opened — a KPI dashboard ("KPI overview", stat tiles + charts)
// built from /api/modules/module-3/dashboard, the same treatment
// MasterData's own module-9/page.tsx and TagScan's own module-1/page.tsx
// give their dashboards. No 403 handling needed here beyond what the
// module's own layout.tsx already does (it checks module access and 403s
// before this ever renders) — the dashboard endpoint is gated the same
// unconditional way.

import { serverApiFetch } from "@/lib/server-api";
import type { InterventionRequestsDashboardStats } from "@/lib/types";
import { InterventionRequestsDashboard } from "@/components/module-3/intervention-requests-dashboard";

export default async function InterventionRequestsLandingPage() {
  const stats = await serverApiFetch<InterventionRequestsDashboardStats>("/api/modules/module-3/dashboard");

  return <InterventionRequestsDashboard stats={stats} />;
}
