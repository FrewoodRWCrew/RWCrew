// Atelier's main page: the KPI overview (see AtelierDashboard). A user without
// the KPI right is sent to the first Atelier screen they may open instead,
// so clicking the tile always lands somewhere useful.

import { getLocale, getTranslations } from "next-intl/server";
import { redirect } from "@/i18n/navigation";
import { serverApiFetch } from "@/lib/server-api";
import type { AtelierMyPermissions } from "@/lib/types";
import { AtelierDashboard } from "@/components/module-5/atelier-dashboard";

// Where to go instead of the KPI page, in menu order.
const FALLBACK_SCREENS: [string, string][] = [
  ["atelier.roles", "/modules/module-5/access-rights/roles"],
  ["atelier.users", "/modules/module-5/access-rights/users"],
];

export default async function AtelierLandingPage() {
  // The layout already refused users without module access, so this call
  // only answers 200 here.
  const permissions = await serverApiFetch<AtelierMyPermissions>("/api/modules/module-5/me/permissions");
  if (!permissions.viewable_screen_keys.includes("atelier.kpi")) {
    const fallback = FALLBACK_SCREENS.find(([key]) => permissions.viewable_screen_keys.includes(key));
    if (fallback) {
      redirect({ href: fallback[1], locale: await getLocale() });
    }
    const tErrors = await getTranslations("errors");
    return <p className="text-sm text-destructive">{tErrors("forbidden")}</p>;
  }

  return <AtelierDashboard />;
}
