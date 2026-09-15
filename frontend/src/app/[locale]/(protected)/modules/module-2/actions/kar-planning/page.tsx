// KarTracker's "Kar Planning" screen: the read-only report joining
// KarManagement with its lookups — see KarPlanning for the actual UI.

import { getTranslations } from "next-intl/server";
import { ServerApiError, serverApiFetch } from "@/lib/server-api";
import type { KarTrackerKarPlanningRow } from "@/lib/types";
import { KarPlanning } from "@/components/module-2/kar-planning";

export default async function KarPlanningPage() {
  const tErrors = await getTranslations("errors");

  let rows: KarTrackerKarPlanningRow[];
  try {
    rows = await serverApiFetch<KarTrackerKarPlanningRow[]>("/api/modules/module-2/kar-planning");
  } catch (error) {
    if (error instanceof ServerApiError && error.status === 403) {
      return <p className="text-sm text-destructive">{tErrors("forbidden")}</p>;
    }
    throw error;
  }

  return <KarPlanning initialRows={rows} />;
}
