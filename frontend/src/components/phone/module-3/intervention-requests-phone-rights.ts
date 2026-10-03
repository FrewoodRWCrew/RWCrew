// What this user may do on Interventie Aanvragen's phone screens, read on
// the server from the module's "me/permissions" endpoint. The phone shows
// the KPI overview (always) and the requests screen ("Akties"): list,
// create and edit — never delete or the PDF.

import { ServerApiError, serverApiFetch } from "@/lib/server-api";
import type { InterventionRequestsMyPermissions } from "@/lib/types";

const REQUESTS_SCREEN = "interventionrequests.requests";

export interface InterventionRequestsPhoneRights {
  canViewRequests: boolean;
  canCreateRequests: boolean;
  canEditRequests: boolean;
}

/** The user's rights, or null when they have no access to the module at all. */
export async function getInterventionRequestsPhoneRights(): Promise<InterventionRequestsPhoneRights | null> {
  try {
    const permissions = await serverApiFetch<InterventionRequestsMyPermissions>(
      "/api/modules/module-3/me/permissions",
    );
    return {
      canViewRequests: permissions.viewable_screen_keys.includes(REQUESTS_SCREEN),
      canCreateRequests: permissions.creatable_screen_keys.includes(REQUESTS_SCREEN),
      canEditRequests: permissions.editable_screen_keys.includes(REQUESTS_SCREEN),
    };
  } catch (error) {
    if (error instanceof ServerApiError && error.status === 403) return null;
    throw error;
  }
}
