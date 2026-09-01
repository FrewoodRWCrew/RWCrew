// TagScan's landing page: the first screen shown when the module is
// opened — a KPI dashboard (stat tiles + charts) built from
// /api/modules/module-1/dashboard. The module's other working feature
// (the CSV source files browser) has its own sidebar link, see
// modules/module-1/files/page.tsx. No 403 handling needed here beyond
// what the module's own layout.tsx already does (it checks module
// access and 403s before this ever renders) — the dashboard endpoint is
// gated the same unconditional way.

import { serverApiFetch } from "@/lib/server-api";
import type { TagDashboardStats } from "@/lib/types";
import { TagDashboard } from "@/components/module-1/tag-dashboard";

export default async function TagscanLandingPage() {
  const stats = await serverApiFetch<TagDashboardStats>("/api/modules/module-1/dashboard");

  return <TagDashboard stats={stats} />;
}
