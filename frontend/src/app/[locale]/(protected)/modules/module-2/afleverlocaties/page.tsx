// KarTracker's "Afleverlocatie" screen: the delivery-location master
// data — see AfleverlocatieManagement for the actual UI.

import { getTranslations } from "next-intl/server";
import { ServerApiError, serverApiFetch } from "@/lib/server-api";
import type { AltsienKernlid, KarTrackerAfleverlocatie, KarTrackerDistributiepunt, KarTrackerZone } from "@/lib/types";
import { AfleverlocatieManagement } from "@/components/module-2/afleverlocatie-management";

export default async function AfleverlocatiesPage() {
  const tErrors = await getTranslations("errors");

  let afleverlocaties: KarTrackerAfleverlocatie[] | null = null;
  let zones: KarTrackerZone[] = [];
  let distributiepunten: KarTrackerDistributiepunt[] = [];
  let altsienKernleden: AltsienKernlid[] = [];
  try {
    // These four are independent of each other, so fetch them concurrently.
    // The required Zone and Distributiepunt lookups must remain available for
    // a delivery-location form; only the optional cross-module lookup may be empty.
    [afleverlocaties, zones, distributiepunten, altsienKernleden] = await Promise.all([
      serverApiFetch<KarTrackerAfleverlocatie[]>("/api/modules/module-2/afleverlocaties"),
      serverApiFetch<KarTrackerZone[]>("/api/modules/module-2/zones"),
      serverApiFetch<KarTrackerDistributiepunt[]>("/api/modules/module-2/distributiepunten"),
      serverApiFetch<AltsienKernlid[]>("/api/modules/module-9/altsien-kernleden").catch(() => []),
    ]);
  } catch (error) {
    if (error instanceof ServerApiError && error.status === 403) {
      return <p className="text-sm text-destructive">{tErrors("forbidden")}</p>;
    }
    throw error;
  }

  return (
    <AfleverlocatieManagement
      initialAfleverlocaties={afleverlocaties}
      zones={zones}
      distributiepunten={distributiepunten}
      altsienKernleden={altsienKernleden}
    />
  );
}
