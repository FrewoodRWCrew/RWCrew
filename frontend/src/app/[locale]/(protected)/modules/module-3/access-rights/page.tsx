// Visiting "Access Rights" itself (rather than its sub-items, "Roles" or
// "Users") just forwards to Roles — same pattern as TagScan's/MasterData's
// own access-rights redirect.

import { getLocale } from "next-intl/server";
import { redirect } from "@/i18n/navigation";

export default async function AccessRightsPage() {
  const locale = await getLocale();
  redirect({ href: "/modules/module-3/access-rights/roles", locale });
}
