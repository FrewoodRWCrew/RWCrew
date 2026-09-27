// KarTracker's "Manuele kar beweging" screen (screen key "kartracker.actions")
// — see KarMovement for the actual UI. The dropdown lists, the movement
// history and the ground plans for the map are fetched here; the user's
// permissions decide whether the logging form and delete buttons show
// (the backend enforces the same rules regardless). Sidebar visibility is
// gated by canViewActions in kartracker-sidebar.tsx.

import { getTranslations } from "next-intl/server";
import { ServerApiError, serverApiFetch } from "@/lib/server-api";
import type {
  KarTrackerGroundplan,
  KarTrackerKarAction,
  KarTrackerKarActionLookups,
  KarTrackerMyPermissions,
} from "@/lib/types";
import { KarMovement } from "@/components/module-2/kar-movement";

export default async function KarMovementPage() {
  const tErrors = await getTranslations("errors");

  let permissions: KarTrackerMyPermissions;
  let lookups: KarTrackerKarActionLookups;
  let actions: KarTrackerKarAction[];
  let groundplans: KarTrackerGroundplan[];
  try {
    [permissions, lookups, actions, groundplans] = await Promise.all([
      serverApiFetch<KarTrackerMyPermissions>("/api/modules/module-2/me/permissions"),
      serverApiFetch<KarTrackerKarActionLookups>("/api/modules/module-2/kar-actions/lookups"),
      serverApiFetch<KarTrackerKarAction[]>("/api/modules/module-2/kar-actions"),
      serverApiFetch<KarTrackerGroundplan[]>("/api/modules/module-2/groundplans"),
    ]);
  } catch (error) {
    if (error instanceof ServerApiError && error.status === 403) {
      return <p className="text-sm text-destructive">{tErrors("forbidden")}</p>;
    }
    throw error;
  }

  return (
    <KarMovement
      lookups={lookups}
      initialActions={actions}
      groundplans={groundplans}
      canCreate={permissions.creatable_screen_keys.includes("kartracker.actions")}
      canDelete={permissions.deletable_screen_keys.includes("kartracker.actions")}
    />
  );
}
