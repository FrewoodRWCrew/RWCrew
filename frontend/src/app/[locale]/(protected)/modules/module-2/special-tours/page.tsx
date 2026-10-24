// KarTracker's "Speciale levertoeren" screen — see SpecialTourManagement for
// the actual UI. Permission-checked the normal module way (via this route's
// layout.tsx), plus its own screen-level check here for direct navigation.

import { getTranslations } from "next-intl/server";
import { ServerApiError, serverApiFetch } from "@/lib/server-api";
import type { KarTrackerSpecialTour } from "@/lib/types";
import { SpecialTourManagement } from "@/components/module-2/special-tour-management";

export default async function SpecialToursPage() {
  const tErrors = await getTranslations("errors");

  let tours: KarTrackerSpecialTour[] | null = null;
  try {
    tours = await serverApiFetch<KarTrackerSpecialTour[]>("/api/modules/module-2/special-tours");
  } catch (error) {
    if (error instanceof ServerApiError && error.status === 403) {
      return <p className="text-sm text-destructive">{tErrors("forbidden")}</p>;
    }
    throw error;
  }

  return <SpecialTourManagement initialTours={tours} />;
}
