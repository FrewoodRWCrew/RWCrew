// StockMaster's "Kar inventarissen": the counts teams made of their own kar on
// the public kar page — see KarInventoriesList.

import { getTranslations } from "next-intl/server";
import { KarInventoriesList } from "@/components/module-4/kar-inventories-list";
import { canView, loadStockMasterPage } from "@/components/module-4/stockmaster-page-data";

export default async function Page() {
  const data = await loadStockMasterPage(canView("karinventories"));
  if (!data) {
    const tErrors = await getTranslations("errors");
    return <p className="text-sm text-destructive">{tErrors("forbidden")}</p>;
  }

  return <KarInventoriesList seasons={data.seasons} />;
}
