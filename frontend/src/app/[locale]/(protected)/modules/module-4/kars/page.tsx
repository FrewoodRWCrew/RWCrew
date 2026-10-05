// StockMaster's "Karren": every kar as a card — see KarOverview.

import { getTranslations } from "next-intl/server";
import { KarOverview } from "@/components/module-4/kar-overview";
import { canView, loadStockMasterPage } from "@/components/module-4/stockmaster-page-data";

export default async function Page() {
  const data = await loadStockMasterPage(canView("kars"));
  if (!data) {
    const tErrors = await getTranslations("errors");
    return <p className="text-sm text-destructive">{tErrors("forbidden")}</p>;
  }

  return <KarOverview seasons={data.seasons} />;
}
