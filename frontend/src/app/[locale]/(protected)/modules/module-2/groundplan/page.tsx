// KarTracker's "Grondplan" screen: the list of ground plans of the event
// site, each with its own image and south-west/north-east corner
// coordinates, so Kar Map can overlay them — see GroundplanManagement for
// the actual UI.

import { getTranslations } from "next-intl/server";
import { ServerApiError, serverApiFetch } from "@/lib/server-api";
import type { KarTrackerGroundplan, KarTrackerMyPermissions } from "@/lib/types";
import { GroundplanManagement } from "@/components/module-2/groundplan-management";

export default async function GroundplanPage() {
  const tErrors = await getTranslations("errors");

  let groundplans: KarTrackerGroundplan[];
  let permissions: KarTrackerMyPermissions;
  try {
    [groundplans, permissions] = await Promise.all([
      serverApiFetch<KarTrackerGroundplan[]>("/api/modules/module-2/groundplans"),
      serverApiFetch<KarTrackerMyPermissions>("/api/modules/module-2/me/permissions"),
    ]);
  } catch (error) {
    if (error instanceof ServerApiError && error.status === 403) {
      return <p className="text-sm text-destructive">{tErrors("forbidden")}</p>;
    }
    throw error;
  }

  // The add/change buttons only show for users whose role allows them;
  // the backend enforces the same rules regardless.
  return (
    <GroundplanManagement
      initialGroundplans={groundplans}
      canCreate={permissions.creatable_screen_keys.includes("kartracker.groundplan")}
      canEdit={permissions.editable_screen_keys.includes("kartracker.groundplan")}
    />
  );
}
