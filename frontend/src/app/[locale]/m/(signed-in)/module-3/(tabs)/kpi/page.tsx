// "KPI overzicht": the module's key figures, open to everyone with access
// to the module (like the desktop dashboard).

import { serverApiFetch } from "@/lib/server-api";
import type { InterventionRequestsDashboardStats } from "@/lib/types";
import { KpiOverview } from "@/components/phone/module-3/kpi-overview";

export default async function InterventionRequestsKpiPage() {
  const stats = await serverApiFetch<InterventionRequestsDashboardStats>("/api/modules/module-3/dashboard");
  return <KpiOverview stats={stats} />;
}
