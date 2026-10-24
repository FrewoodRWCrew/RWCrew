// KarTracker's "Leveringsvolgorde" screen: the order of the delivery tour
// across the ground — see DeliveryOrderScreen for the actual UI. The active
// delivery locations, the user's edit right and the ground plans (for the
// screen's "Kaart") are fetched here.

import { getTranslations } from "next-intl/server";
import { ServerApiError, serverApiFetch } from "@/lib/server-api";
import type { KarTrackerDeliveryOrderLocation, KarTrackerGroundplan, KarTrackerMyPermissions } from "@/lib/types";
import { DeliveryOrderScreen } from "@/components/module-2/delivery-order-screen";

export default async function DeliveryOrderPage() {
  const tErrors = await getTranslations("errors");

  let locations: KarTrackerDeliveryOrderLocation[];
  let permissions: KarTrackerMyPermissions;
  let groundplans: KarTrackerGroundplan[];
  try {
    [locations, permissions, groundplans] = await Promise.all([
      serverApiFetch<KarTrackerDeliveryOrderLocation[]>("/api/modules/module-2/delivery-order"),
      serverApiFetch<KarTrackerMyPermissions>("/api/modules/module-2/me/permissions"),
      // Without ground plans the map just shows the street map.
      serverApiFetch<KarTrackerGroundplan[]>("/api/modules/module-2/groundplans").catch(() => []),
    ]);
  } catch (error) {
    if (error instanceof ServerApiError && error.status === 403) {
      return <p className="text-sm text-destructive">{tErrors("forbidden")}</p>;
    }
    throw error;
  }

  return (
    <DeliveryOrderScreen
      initialLocations={locations}
      canEdit={permissions.editable_screen_keys.includes("kartracker.leveringsvolgorde")}
      groundplans={groundplans}
    />
  );
}
