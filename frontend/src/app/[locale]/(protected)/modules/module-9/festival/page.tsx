// MasterData's "Festivals" screen: a table of festivals with add/change/
// delete, each tied to a season — see FestivalManagement for the actual UI.
// Follows the same server-fetch pattern as products/page.tsx, since a
// festival's Season dropdown needs the Season list fetched alongside it.

import { getTranslations } from "next-intl/server";
import { ServerApiError, serverApiFetch } from "@/lib/server-api";
import type { Festival, Season } from "@/lib/types";
import { FestivalManagement } from "@/components/module-9/festival-management";

export default async function MasterDataFestivalPage() {
  const tErrors = await getTranslations("errors");

  let festivals: Festival[] | null = null;
  let seasons: Season[] = [];
  try {
    festivals = await serverApiFetch<Festival[]>("/api/modules/module-9/festivals");
    // The Season list powers the Season dropdown on the create/edit form —
    // fetched here too since a user might manage festivals without also
    // being able to view the Season screen directly.
    seasons = await serverApiFetch<Season[]>("/api/modules/module-9/seasons").catch(() => []);
  } catch (error) {
    if (error instanceof ServerApiError && error.status === 403) {
      return <p className="text-sm text-destructive">{tErrors("forbidden")}</p>;
    }
    throw error;
  }

  return <FestivalManagement initialFestivals={festivals} seasons={seasons} />;
}
