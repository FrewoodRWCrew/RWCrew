// Visiting "Access Rights" itself (rather than its sub-items, "Roles" or
// "Users") just forwards to Roles — same pattern as TagScan's/MasterData's
// own access-rights redirect.

import { getLocale } from "next-intl/server";
import { redirect } from "@/i18n/navigation";
import { serverApiFetch } from "@/lib/server-api";
import type { AtelierMyPermissions } from "@/lib/types";

export default async function AccessRightsPage() {
  const locale = await getLocale();
  const permissions = await serverApiFetch<AtelierMyPermissions>("/api/modules/module-5/me/permissions");
  const href = permissions.viewable_screen_keys.includes("atelier.roles")
    ? "/modules/module-5/access-rights/roles"
    : permissions.viewable_screen_keys.includes("atelier.users")
      ? "/modules/module-5/access-rights/users"
      : "/modules/module-5";
  redirect({ href, locale });
}
