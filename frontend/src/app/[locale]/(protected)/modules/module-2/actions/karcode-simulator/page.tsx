// KarTracker's "Karcode Simulator" screen (screen key
// "kartracker.karcodesimulator") — see KarcodeSimulator for the actual UI.
// The permissions are checked here so a user without the right gets the
// usual "forbidden" text instead of a calculator that only shows errors
// (the backend enforces the same rule on every code request). Sidebar
// visibility is gated by canViewKarcodeSimulator in kartracker-sidebar.tsx.

import { getTranslations } from "next-intl/server";
import { ServerApiError, serverApiFetch } from "@/lib/server-api";
import type { KarTrackerMyPermissions } from "@/lib/types";
import { KarcodeSimulator } from "@/components/module-2/karcode-simulator";

export default async function KarcodeSimulatorPage() {
  const tErrors = await getTranslations("errors");

  let permissions: KarTrackerMyPermissions;
  try {
    permissions = await serverApiFetch<KarTrackerMyPermissions>(
      "/api/modules/module-2/me/permissions",
    );
  } catch (error) {
    if (error instanceof ServerApiError && error.status === 403) {
      return <p className="text-sm text-destructive">{tErrors("forbidden")}</p>;
    }
    throw error;
  }
  if (
    !permissions.viewable_screen_keys.includes("kartracker.karcodesimulator")
  ) {
    return <p className="text-sm text-destructive">{tErrors("forbidden")}</p>;
  }

  return <KarcodeSimulator />;
}
