// Visiting "Access Rights" itself (rather than its one sub-item,
// "Roles") just forwards there — same pattern as the site-wide
// "/admin/master-data" redirect.

import { getLocale } from "next-intl/server";
import { redirect } from "@/i18n/navigation";

export default async function AccessRightsPage() {
  const locale = await getLocale();
  redirect({ href: "/modules/module-1/access-rights/roles", locale });
}
