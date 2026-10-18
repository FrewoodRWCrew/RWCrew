// KarTracker's "Plan a kar" screen: an overview of every kar with its team's
// planning progress, and per team the delivery location (afleverlocatie) for
// each of its festivals of the selected season — see PlanKarScreen for the
// switch between both. The teams and location dropdown list are fetched here;
// the overview and matrix are loaded client-side (they depend on the season
// picked in the header, which only the browser knows). The ground plans are
// fetched here too, for the map of chosen locations below the matrix.

import { getTranslations } from "next-intl/server";
import { ServerApiError, serverApiFetch } from "@/lib/server-api";
import type {
  KarTrackerGroundplan,
  KarTrackerPlanKarAfleverlocatieOption,
  KarTrackerPlanKarOption,
} from "@/lib/types";
import { PlanKarScreen } from "@/components/module-2/plan-kar-screen";

export default async function PlanKarPage() {
  const tErrors = await getTranslations("errors");

  let teams: KarTrackerPlanKarOption[];
  let afleverlocaties: KarTrackerPlanKarAfleverlocatieOption[];
  let groundplans: KarTrackerGroundplan[];
  try {
    [teams, afleverlocaties, groundplans] = await Promise.all([
      serverApiFetch<KarTrackerPlanKarOption[]>("/api/modules/module-2/plan-kar/teams"),
      serverApiFetch<KarTrackerPlanKarAfleverlocatieOption[]>("/api/modules/module-2/plan-kar/afleverlocaties"),
      serverApiFetch<KarTrackerGroundplan[]>("/api/modules/module-2/groundplans"),
    ]);
  } catch (error) {
    if (error instanceof ServerApiError && error.status === 403) {
      return <p className="text-sm text-destructive">{tErrors("forbidden")}</p>;
    }
    throw error;
  }

  return <PlanKarScreen teams={teams} afleverlocaties={afleverlocaties} groundplans={groundplans} />;
}
