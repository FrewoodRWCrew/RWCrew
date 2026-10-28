// What this user may do on StockMaster's phone screens, read on the server
// from the same "me/permissions" endpoint the desktop sidebar uses. The
// phone has one StockMaster screen: the voice count ("Spraaktelling").

import { ServerApiError, serverApiFetch } from "@/lib/server-api";
import type { StockMasterMyPermissions } from "@/lib/types";

const VOICE_COUNT_SCREEN = "stockmaster.voicecount";

export interface StockMasterPhoneRights {
  /** "create" on the voice count screen = may count a kar on the phone. */
  canVoiceCount: boolean;
}

/** The user's StockMaster rights, or null when they have no access to the module at all. */
export async function getStockMasterPhoneRights(): Promise<StockMasterPhoneRights | null> {
  try {
    const permissions = await serverApiFetch<StockMasterMyPermissions>("/api/modules/module-4/me/permissions");
    return {
      canVoiceCount: permissions.creatable_screen_keys.includes(VOICE_COUNT_SCREEN),
    };
  } catch (error) {
    if (error instanceof ServerApiError && error.status === 403) return null;
    throw error;
  }
}
