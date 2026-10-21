// KarTracker's entry point (the landing tile's target): opens the module on
// Kar Planning. A user without the Kar Planning right lands on the KPI
// dashboard instead, which every module member may open. A user without
// module access stays here: the module's layout.tsx shows the forbidden
// message on the permissions call's 403, so this page renders nothing.

import { getLocale } from "next-intl/server";
import { redirect } from "@/i18n/navigation";
import { ServerApiError, serverApiFetch } from "@/lib/server-api";
import type { KarTrackerMyPermissions } from "@/lib/types";

export default async function KarTrackerLandingPage() {
  let permissions: KarTrackerMyPermissions;
  try {
    permissions = await serverApiFetch<KarTrackerMyPermissions>("/api/modules/module-2/me/permissions");
  } catch (error) {
    // No module access: the layout already shows the forbidden message.
    if (error instanceof ServerApiError && error.status === 403) return null;
    throw error;
  }

  const href = permissions.viewable_screen_keys.includes("kartracker.karplanning")
    ? "/modules/module-2/actions/kar-planning"
    : "/modules/module-2/dashboard";
  redirect({ href, locale: await getLocale() });
}
