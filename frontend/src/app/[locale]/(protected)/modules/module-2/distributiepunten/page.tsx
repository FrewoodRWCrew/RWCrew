// KarTracker's "Distributiepunten" screen: the distribution-point master
// data — see DistributiepuntManagement for the actual UI.

import { getTranslations } from "next-intl/server";
import { ServerApiError, serverApiFetch } from "@/lib/server-api";
import type { AltsienKernlid, KarTrackerDistributiepunt } from "@/lib/types";
import { DistributiepuntManagement } from "@/components/module-2/distributiepunt-management";

export default async function DistributiepuntenPage() {
  const tErrors = await getTranslations("errors");

  let distributiepunten: KarTrackerDistributiepunt[] | null = null;
  let altsienKernleden: AltsienKernlid[] = [];
  try {
    // Independent of each other, so fetch concurrently. The Altsien
    // Kernleden lookup is caught separately so a failure there just
    // leaves the dropdown empty instead of breaking the screen.
    [distributiepunten, altsienKernleden] = await Promise.all([
      serverApiFetch<KarTrackerDistributiepunt[]>("/api/modules/module-2/distributiepunten"),
      serverApiFetch<AltsienKernlid[]>("/api/modules/altsien-kernleden").catch(() => []),
    ]);
  } catch (error) {
    if (error instanceof ServerApiError && error.status === 403) {
      return <p className="text-sm text-destructive">{tErrors("forbidden")}</p>;
    }
    throw error;
  }

  return (
    <DistributiepuntManagement initialDistributiepunten={distributiepunten} altsienKernleden={altsienKernleden} />
  );
}
