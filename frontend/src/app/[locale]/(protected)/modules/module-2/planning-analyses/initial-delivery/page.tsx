// KarTracker's "Initiële leverplanning" screen (Planningsanalyses group) —
// see InitialDeliveryScreen for the actual UI. The data depends on the
// header's season (only known in the browser), so the screen loads it
// itself; here only the right on the screen is checked.

import { getTranslations } from "next-intl/server";
import { serverApiFetch } from "@/lib/server-api";
import type { KarTrackerMyPermissions } from "@/lib/types";
import { InitialDeliveryScreen } from "@/components/module-2/initial-delivery-screen";

export default async function InitialDeliveryPage() {
  const tErrors = await getTranslations("errors");

  const permissions = await serverApiFetch<KarTrackerMyPermissions>("/api/modules/module-2/me/permissions");
  if (!permissions.viewable_screen_keys.includes("kartracker.initieleleverplanning")) {
    return <p className="text-sm text-destructive">{tErrors("forbidden")}</p>;
  }

  return <InitialDeliveryScreen />;
}
