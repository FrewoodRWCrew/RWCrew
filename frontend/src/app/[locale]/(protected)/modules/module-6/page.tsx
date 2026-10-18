// Walkies's main page: the KPI overview (see WalkiesDashboard). A user without
// the KPI right is sent to the first Walkies screen they may open instead,
// so clicking the tile always lands somewhere useful.

import { getLocale, getTranslations } from "next-intl/server";
import { redirect } from "@/i18n/navigation";
import { serverApiFetch } from "@/lib/server-api";
import type { WalkiesMyPermissions } from "@/lib/types";
import { WalkiesDashboard } from "@/components/module-6/walkies-dashboard";

// Where to go instead of the KPI page, in menu order.
const FALLBACK_SCREENS: [string, string][] = [
  ["walkies.roles", "/modules/module-6/access-rights/roles"],
  ["walkies.users", "/modules/module-6/access-rights/users"],
];

export default async function WalkiesLandingPage() {
  // The layout already refused users without module access, so this call
  // only answers 200 here.
  const permissions = await serverApiFetch<WalkiesMyPermissions>("/api/modules/module-6/me/permissions");
  if (!permissions.viewable_screen_keys.includes("walkies.kpi")) {
    const fallback = FALLBACK_SCREENS.find(([key]) => permissions.viewable_screen_keys.includes(key));
    if (fallback) {
      redirect({ href: fallback[1], locale: await getLocale() });
    }
    const tErrors = await getTranslations("errors");
    return <p className="text-sm text-destructive">{tErrors("forbidden")}</p>;
  }

  return <WalkiesDashboard />;
}
