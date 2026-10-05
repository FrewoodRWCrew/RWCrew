// StockMaster's "Voorraadoverzicht" — see StockOverview.

import { getTranslations } from "next-intl/server";
import { StockOverview } from "@/components/module-4/stock-overview";
import { canView, loadStockMasterPage } from "@/components/module-4/stockmaster-page-data";

export default async function Page() {
  const data = await loadStockMasterPage(canView("stock"));
  if (!data) {
    const tErrors = await getTranslations("errors");
    return <p className="text-sm text-destructive">{tErrors("forbidden")}</p>;
  }

  return <StockOverview permissions={data.permissions} />;
}
