// KarTracker's "Zone" screen — see ZoneManagement for the actual UI.
// Permission-checked the normal module way (via this route's layout.tsx),
// plus its own screen-level check here for direct navigation.

import { getTranslations } from "next-intl/server";
import { ServerApiError, serverApiFetch } from "@/lib/server-api";
import type { KarTrackerZone } from "@/lib/types";
import { ZoneManagement } from "@/components/module-2/zone-management";

export default async function ZonesPage() {
  const tErrors = await getTranslations("errors");

  let zones: KarTrackerZone[] | null = null;
  try {
    zones = await serverApiFetch<KarTrackerZone[]>("/api/modules/module-2/zones");
  } catch (error) {
    if (error instanceof ServerApiError && error.status === 403) {
      return <p className="text-sm text-destructive">{tErrors("forbidden")}</p>;
    }
    throw error;
  }

  return <ZoneManagement initialZones={zones} />;
}
