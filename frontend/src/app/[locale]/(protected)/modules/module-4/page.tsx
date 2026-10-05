// StockMaster's main page: the KPI dashboard (see StockMasterDashboard).
// A user without the KPI right is sent to the first StockMaster screen they
// may open instead, so clicking the tile always lands somewhere useful.

import { getLocale, getTranslations } from "next-intl/server";
import { redirect } from "@/i18n/navigation";
import { StockMasterDashboard } from "@/components/module-4/stockmaster-dashboard";
import { loadStockMasterPage } from "@/components/module-4/stockmaster-page-data";

// Where to go instead of the KPI page, in menu order.
const FALLBACK_SCREENS: [string, string][] = [
  ["stockmaster.stock", "/modules/module-4/stock"],
  ["stockmaster.kars", "/modules/module-4/kars"],
  ["stockmaster.count", "/modules/module-4/count"],
  ["stockmaster.requirements", "/modules/module-4/requirements"],
  ["stockmaster.orderneeds", "/modules/module-4/order-needs"],
  ["stockmaster.bookings", "/modules/module-4/bookings"],
  ["stockmaster.reasons", "/modules/module-4/settings/reasons"],
  ["stockmaster.roles", "/modules/module-4/access-rights/roles"],
  ["stockmaster.users", "/modules/module-4/access-rights/users"],
];

export default async function StockMasterLandingPage() {
  const data = await loadStockMasterPage(() => true);
  if (data && !data.permissions.viewable_screen_keys.includes("stockmaster.kpi")) {
    const fallback = FALLBACK_SCREENS.find(([key]) => data.permissions.viewable_screen_keys.includes(key));
    if (fallback) {
      redirect({ href: fallback[1], locale: await getLocale() });
    }
    const tErrors = await getTranslations("errors");
    return <p className="text-sm text-destructive">{tErrors("forbidden")}</p>;
  }
  if (!data) {
    const tErrors = await getTranslations("errors");
    return <p className="text-sm text-destructive">{tErrors("forbidden")}</p>;
  }

  return <StockMasterDashboard seasons={data.seasons} />;
}
