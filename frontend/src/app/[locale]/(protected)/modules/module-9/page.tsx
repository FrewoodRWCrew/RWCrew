// MasterData's "Season" screen: reachable directly at the module's own
// root URL, the same way TagScan's Dashboard is its module's root page —
// see SeasonManagement for the actual UI. Moved here from
// admin/master-data/season/page.tsx, now permission-checked the normal
// module way (via this route's layout.tsx) instead of a raw
// is_super_admin check.

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
