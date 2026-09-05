// MasterData's "Season" screen — see SeasonManagement for the actual UI.
// Used to live at the module's own root URL; moved here once "Masterdata
// Overview" (the KPI dashboard) took over that spot, the same way
// TagScan's own screens each get their own route under its Dashboard
// landing page. Still permission-checked the normal module way (via this
// route's layout.tsx).

import { getTranslations } from "next-intl/server";
import { ServerApiError, serverApiFetch } from "@/lib/server-api";
import type { Season } from "@/lib/types";
import { SeasonManagement } from "@/components/module-9/season-management";

export default async function MasterDataSeasonPage() {
  const tErrors = await getTranslations("errors");

  let seasons: Season[] | null = null;
  try {
    seasons = await serverApiFetch<Season[]>("/api/modules/module-9/seasons");
  } catch (error) {
    if (error instanceof ServerApiError && error.status === 403) {
      return <p className="text-sm text-destructive">{tErrors("forbidden")}</p>;
    }
    throw error;
  }

  return <SeasonManagement initialSeasons={seasons} />;
}
