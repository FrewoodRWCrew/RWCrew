// KarTracker's "Kar Planning" screen: the read-only report joining
// KarManagement with its lookups — see KarPlanning for the actual UI.

import { getTranslations } from "next-intl/server";
import { ServerApiError, serverApiFetch } from "@/lib/server-api";
import type { KarTrackerKarPlanningReport } from "@/lib/types";
import { KarPlanning } from "@/components/module-2/kar-planning";

export default async function KarPlanningPage() {
  const tErrors = await getTranslations("errors");

  // Fetched without a season (the header's season only lives in the browser),
  // so this has no festival columns; KarPlanning re-fetches with the selected
  // season once it knows it.
  let report: KarTrackerKarPlanningReport;
  try {
    report = await serverApiFetch<KarTrackerKarPlanningReport>("/api/modules/module-2/kar-planning");
  } catch (error) {
    if (error instanceof ServerApiError && error.status === 403) {
      return <p className="text-sm text-destructive">{tErrors("forbidden")}</p>;
    }
    throw error;
  }

  return <KarPlanning initialReport={report} />;
}
