// Visiting "Access Rights" itself (rather than its sub-items, "Roles" or
// "Users") just forwards to Roles — same pattern as Intervention Requests'/
// TagScan's/MasterData's own access-rights redirect.

import { getLocale } from "next-intl/server";
import { redirect } from "@/i18n/navigation";
import { serverApiFetch } from "@/lib/server-api";
import type { KarTrackerMyPermissions } from "@/lib/types";

export default async function AccessRightsPage() {
  const locale = await getLocale();
  const permissions = await serverApiFetch<KarTrackerMyPermissions>("/api/modules/module-2/me/permissions");
  const href = permissions.viewable_screen_keys.includes("kartracker.roles")
    ? "/modules/module-2/access-rights/roles"
    : permissions.viewable_screen_keys.includes("kartracker.users")
      ? "/modules/module-2/access-rights/users"
      : "/modules/module-2";
  redirect({ href, locale });
}
