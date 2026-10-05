// StockMaster's "Telling" (stock count) — see CountPanel.

import { getTranslations } from "next-intl/server";
import { CountPanel } from "@/components/module-4/count-panel";
import { canView, loadStockMasterPage } from "@/components/module-4/stockmaster-page-data";

export default async function Page() {
  const data = await loadStockMasterPage(canView("count"));
  if (!data) {
    const tErrors = await getTranslations("errors");
    return <p className="text-sm text-destructive">{tErrors("forbidden")}</p>;
  }

  return <CountPanel seasons={data.seasons} permissions={data.permissions} />;
}
