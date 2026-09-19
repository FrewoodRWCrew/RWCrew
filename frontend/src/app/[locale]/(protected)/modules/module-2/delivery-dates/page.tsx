// KarTracker's "Delivery Dates" screen: per active festival of the season
// selected in the header, a delivery date and a pick-up date — see
// DeliveryDates for the actual UI. The table itself is loaded client-side,
// since it depends on the header's season, which only the browser knows.
// This page only checks the screen permission (by probing the view
// endpoint) so direct navigation without access shows the "forbidden" note.

import { getTranslations } from "next-intl/server";
import { ServerApiError, serverApiFetch } from "@/lib/server-api";
import { DeliveryDates } from "@/components/module-2/delivery-dates";
import type { KarTrackerMyPermissions } from "@/lib/types";

export default async function DeliveryDatesPage() {
  const tErrors = await getTranslations("errors");
  const permissions = await serverApiFetch<KarTrackerMyPermissions>("/api/modules/module-2/me/permissions");

  try {
    // season_id 0 never exists: a 404 means "allowed, just no such season",
    // while a 403 means the user lacks the screen permission.
    await serverApiFetch("/api/modules/module-2/leverdata?season_id=0");
  } catch (error) {
    if (error instanceof ServerApiError && error.status === 403) {
      return <p className="text-sm text-destructive">{tErrors("forbidden")}</p>;
    }
    if (!(error instanceof ServerApiError && error.status === 404)) {
      throw error;
    }
  }

  return <DeliveryDates canEdit={permissions.editable_screen_keys.includes("kartracker.leverdata")} />;
}
