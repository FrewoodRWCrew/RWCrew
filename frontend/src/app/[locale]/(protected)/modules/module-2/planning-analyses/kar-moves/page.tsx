// KarTracker's "Verplaatsingen tussen festivals" screen (Planningsanalyses
// group) — see KarMovesScreen for the actual UI. The data depends on the
// header's season and the chosen festivals (only known in the browser), so
// the screen loads it itself; here only the right on the screen is checked.

import { getTranslations } from "next-intl/server";
import { serverApiFetch } from "@/lib/server-api";
import type { KarTrackerMyPermissions } from "@/lib/types";
import { KarMovesScreen } from "@/components/module-2/kar-moves-screen";

export default async function KarMovesPage() {
  const tErrors = await getTranslations("errors");

  const permissions = await serverApiFetch<KarTrackerMyPermissions>("/api/modules/module-2/me/permissions");
  if (!permissions.viewable_screen_keys.includes("kartracker.karverplaatsingen")) {
    return <p className="text-sm text-destructive">{tErrors("forbidden")}</p>;
  }

  return <KarMovesScreen />;
}
