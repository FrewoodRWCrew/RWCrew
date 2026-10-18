// Visiting "Access Rights" itself (rather than its sub-items, "Roles" or
// "Users") just forwards to Roles — same pattern as TagScan's/MasterData's
// own access-rights redirect.

import { getLocale } from "next-intl/server";
import { redirect } from "@/i18n/navigation";
import { serverApiFetch } from "@/lib/server-api";
import type { WalkiesMyPermissions } from "@/lib/types";

export default async function AccessRightsPage() {
  const locale = await getLocale();
  const permissions = await serverApiFetch<WalkiesMyPermissions>("/api/modules/module-6/me/permissions");
  const href = permissions.viewable_screen_keys.includes("walkies.roles")
    ? "/modules/module-6/access-rights/roles"
    : permissions.viewable_screen_keys.includes("walkies.users")
      ? "/modules/module-6/access-rights/users"
      : "/modules/module-6";
  redirect({ href, locale });
}
