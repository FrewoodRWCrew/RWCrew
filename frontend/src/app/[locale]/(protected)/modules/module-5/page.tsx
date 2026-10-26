// Atelier's main page: the KPI overview (see AtelierDashboard). A user without
// the KPI right is sent to the first Atelier screen they may open instead,
// so clicking the tile always lands somewhere useful.

import { getLocale, getTranslations } from "next-intl/server";
import { redirect } from "@/i18n/navigation";
import { serverApiFetch } from "@/lib/server-api";
import type { AtelierMyPermissions, Season } from "@/lib/types";
import { AtelierDashboard } from "@/components/module-5/atelier-dashboard";

// Where to go instead of the KPI page, in menu order.
const FALLBACK_SCREENS: [string, string][] = [
  ["atelier.desk", "/modules/module-5/desk"],
  ["atelier.open", "/modules/module-5/desk/open"],
  ["atelier.reservations", "/modules/module-5/reservations"],
  ["atelier.preparation", "/modules/module-5/reservations/preparation"],
  ["atelier.stock", "/modules/module-5/stock"],
  ["atelier.receipt", "/modules/module-5/stock/receipt"],
  ["atelier.wash", "/modules/module-5/stock/wash"],
  ["atelier.writeoff", "/modules/module-5/stock/write-off"],
  ["atelier.count", "/modules/module-5/stock/count"],
  ["atelier.bookings", "/modules/module-5/stock/bookings"],
  ["atelier.orderneeds", "/modules/module-5/stock/order-needs"],
  ["atelier.articles", "/modules/module-5/masterdata/articles"],
  ["atelier.sizes", "/modules/module-5/masterdata/articles/sizes"],
  ["atelier.dataupload", "/modules/module-5/masterdata/data-upload-download"],
  ["atelier.settings", "/modules/module-5/settings"],
  ["atelier.scantest", "/modules/module-5/settings/scan-test"],
  ["atelier.mailtemplates", "/modules/module-5/settings/mails"],
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

  const seasons = await serverApiFetch<Season[]>("/api/modules/module-5/seasons");
  return <AtelierDashboard seasons={seasons} />;
}
