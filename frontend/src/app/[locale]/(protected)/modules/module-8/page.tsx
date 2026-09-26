// Altsien Select's landing page: the KPI dashboard ("KPI overzicht") —
// wizard progress and special requests for the chosen season, limited to
// the teams the user can see. The module's own layout.tsx already checked
// module access; the dashboard itself is gated by plain module access too.

import { serverApiFetch } from "@/lib/server-api";
import type { Season } from "@/lib/types";
import { AltsienSelectDashboard } from "@/components/module-8/altsien-select-dashboard";

export default async function AltsienSelectLandingPage() {
  const seasons = await serverApiFetch<Season[]>("/api/modules/module-8/seasons");

  return <AltsienSelectDashboard seasons={seasons} />;
}
