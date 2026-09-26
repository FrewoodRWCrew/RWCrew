// KarTracker's "Plan a kar" screen: per team, pick the delivery location
// (afleverlocatie) for every active festival of the selected season — see
// PlanKar for the actual UI. The team and location dropdown lists are
// fetched here; the matrix itself is loaded client-side once a team is
// chosen (it depends on the season picked in the header, which only the
// browser knows).

import { getTranslations } from "next-intl/server";
import { ServerApiError, serverApiFetch } from "@/lib/server-api";
import type { KarTrackerPlanKarAfleverlocatieOption, KarTrackerPlanKarOption } from "@/lib/types";
import { PlanKar } from "@/components/module-2/plan-kar";

export default async function PlanKarPage() {
  const tErrors = await getTranslations("errors");

  let teams: KarTrackerPlanKarOption[];
  let afleverlocaties: KarTrackerPlanKarAfleverlocatieOption[];
  try {
    [teams, afleverlocaties] = await Promise.all([
      serverApiFetch<KarTrackerPlanKarOption[]>("/api/modules/module-2/plan-kar/teams"),
      serverApiFetch<KarTrackerPlanKarAfleverlocatieOption[]>("/api/modules/module-2/plan-kar/afleverlocaties"),
    ]);
  } catch (error) {
    if (error instanceof ServerApiError && error.status === 403) {
      return <p className="text-sm text-destructive">{tErrors("forbidden")}</p>;
    }
    throw error;
  }

  return <PlanKar teams={teams} afleverlocaties={afleverlocaties} />;
}
