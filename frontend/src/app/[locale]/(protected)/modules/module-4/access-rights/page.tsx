// Visiting "Access Rights" itself (rather than its sub-items, "Roles" or
// "Users") just forwards to Roles — same pattern as TagScan's/MasterData's
// own access-rights redirect.

import { getLocale } from "next-intl/server";
import { redirect } from "@/i18n/navigation";
import { serverApiFetch } from "@/lib/server-api";
import type { StockMasterMyPermissions } from "@/lib/types";

export default async function AccessRightsPage() {
  const locale = await getLocale();
  const permissions = await serverApiFetch<StockMasterMyPermissions>("/api/modules/module-4/me/permissions");
  const href = permissions.viewable_screen_keys.includes("stockmaster.roles")
    ? "/modules/module-4/access-rights/roles"
    : permissions.viewable_screen_keys.includes("stockmaster.users")
      ? "/modules/module-4/access-rights/users"
      : "/modules/module-4";
  redirect({ href, locale });
}
