// Server-side helper for Atelier's pages (server components only): load the
// user's Atelier rights and the season list in one go, and tell whether the
// page may be shown at all. Keeps every page.tsx a few lines.

import { serverApiFetch } from "@/lib/server-api";
import type { AtelierMyPermissions, Season } from "@/lib/types";

export interface AtelierPageData {
  permissions: AtelierMyPermissions;
  seasons: Season[];
}

/** The rights and seasons, or null when the user may not view `atelier.<screen>`. */
export async function loadAtelierPage(screen: string): Promise<AtelierPageData | null> {
  const permissions = await serverApiFetch<AtelierMyPermissions>("/api/modules/module-5/me/permissions");
  if (!permissions.viewable_screen_keys.includes(`atelier.${screen}`)) return null;
  const seasons = await serverApiFetch<Season[]>("/api/modules/module-5/seasons");
  return { permissions, seasons };
}

/** Whether the user may perform `action` on `atelier.<screen>`. */
export function atelierCan(
  permissions: AtelierMyPermissions,
  screen: string,
  action: "create" | "edit" | "delete",
): boolean {
  const keys = {
    create: permissions.creatable_screen_keys,
    edit: permissions.editable_screen_keys,
    delete: permissions.deletable_screen_keys,
  }[action];
  return keys.includes(`atelier.${screen}`);
}
