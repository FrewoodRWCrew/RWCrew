// KarTracker's "Kar Map" screen: a map view of Karren, Afleverlocaties and
// Distributiepunten that have coordinates — see KarMap for the actual UI.

import { getTranslations } from "next-intl/server";
import { ServerApiError, serverApiFetch } from "@/lib/server-api";
import type { KarTrackerGroundplan, KarTrackerKarMapResponse } from "@/lib/types";
import { KarMap } from "@/components/module-2/kar-map";

export default async function KarMapPage() {
  const tErrors = await getTranslations("errors");

  let data: KarTrackerKarMapResponse;
  let groundplan: KarTrackerGroundplan;
  try {
    [data, groundplan] = await Promise.all([
      serverApiFetch<KarTrackerKarMapResponse>("/api/modules/module-2/kar-map"),
      serverApiFetch<KarTrackerGroundplan>("/api/modules/module-2/groundplan"),
    ]);
  } catch (error) {
    if (error instanceof ServerApiError && error.status === 403) {
      return <p className="text-sm text-destructive">{tErrors("forbidden")}</p>;
    }
    throw error;
  }

  return <KarMap initialData={data} groundplan={groundplan} />;
}
