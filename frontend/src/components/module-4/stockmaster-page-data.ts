// Server-side helper for StockMaster's pages (server components only): load
// the user's StockMaster rights and the season list in one go, and tell
// whether the page may be shown at all. Keeps every page.tsx a few lines.

import { serverApiFetch } from "@/lib/server-api";
import type { Season, StockMasterMyPermissions } from "@/lib/types";

export interface StockMasterPageData {
  permissions: StockMasterMyPermissions;
  seasons: Season[];
}

/** The rights and seasons, or null when `allowed` says the page is off-limits. */
export async function loadStockMasterPage(
  allowed: (permissions: StockMasterMyPermissions) => boolean,
): Promise<StockMasterPageData | null> {
  const permissions = await serverApiFetch<StockMasterMyPermissions>("/api/modules/module-4/me/permissions");
  if (!allowed(permissions)) return null;
  const seasons = await serverApiFetch<Season[]>("/api/modules/module-4/seasons");
  return { permissions, seasons };
}

/** "Can view stockmaster.<screen>" as a page check. */
export function canView(screen: string) {
  return (permissions: StockMasterMyPermissions) =>
    permissions.viewable_screen_keys.includes(`stockmaster.${screen}`);
}
