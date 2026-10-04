// What this user may do on KarTracker's phone screens, read on the server
// from the same "me/permissions" endpoint the desktop sidebar uses. The
// phone shows three web screens: Manuele kar beweging (as KarScan), Kar
// Planning and Kar Map.

import { ServerApiError, serverApiFetch } from "@/lib/server-api";
import type { KarTrackerMyPermissions } from "@/lib/types";

const ACTIONS_SCREEN = "kartracker.actions";
const KARPLANNING_SCREEN = "kartracker.karplanning";
const KARMAP_SCREEN = "kartracker.karmap";

export interface KarTrackerPhoneRights {
  canViewActions: boolean;
  canCreateActions: boolean;
  canViewPlanning: boolean;
  canViewMap: boolean;
}

/** The user's KarTracker rights, or null when they have no access to the module at all. */
export async function getKarTrackerPhoneRights(): Promise<KarTrackerPhoneRights | null> {
  try {
    const permissions = await serverApiFetch<KarTrackerMyPermissions>("/api/modules/module-2/me/permissions");
    return {
      canViewActions: permissions.viewable_screen_keys.includes(ACTIONS_SCREEN),
      canCreateActions: permissions.creatable_screen_keys.includes(ACTIONS_SCREEN),
      canViewPlanning: permissions.viewable_screen_keys.includes(KARPLANNING_SCREEN),
      canViewMap: permissions.viewable_screen_keys.includes(KARMAP_SCREEN),
    };
  } catch (error) {
    if (error instanceof ServerApiError && error.status === 403) return null;
    throw error;
  }
}
