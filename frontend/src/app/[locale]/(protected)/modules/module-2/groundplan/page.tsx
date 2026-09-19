// KarTracker's "Grondplan" screen: lets an admin upload the event site's
// ground-plan image and set its south-west/north-east corner coordinates,
// so Kar Map can overlay it — see GroundplanSettings for the actual UI.

import { getTranslations } from "next-intl/server";
import { ServerApiError, serverApiFetch } from "@/lib/server-api";
import type { KarTrackerGroundplan } from "@/lib/types";
import { GroundplanSettings } from "@/components/module-2/groundplan-settings";

export default async function GroundplanPage() {
  const tErrors = await getTranslations("errors");

  let groundplan: KarTrackerGroundplan;
  try {
    groundplan = await serverApiFetch<KarTrackerGroundplan>("/api/modules/module-2/groundplan");
  } catch (error) {
    if (error instanceof ServerApiError && error.status === 403) {
      return <p className="text-sm text-destructive">{tErrors("forbidden")}</p>;
    }
    throw error;
  }

  return <GroundplanSettings initialData={groundplan} />;
}
