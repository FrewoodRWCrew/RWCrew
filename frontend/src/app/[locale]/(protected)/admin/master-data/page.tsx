// Visiting "Master Data" itself (rather than one of its sub-items, e.g.
// "Season", in the admin sidebar) just forwards to the first sub-item —
// there's currently nothing to show on this exact page. This also keeps
// the old bookmarkable "/admin/master-data" URL working.

import { getLocale } from "next-intl/server";
import { redirect } from "@/i18n/navigation";

export default async function MasterDataPage() {
  const locale = await getLocale();
  redirect({ href: "/admin/master-data/season", locale });
}
