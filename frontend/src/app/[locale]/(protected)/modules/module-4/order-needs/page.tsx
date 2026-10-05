// StockMaster's "Te bestellen": needs versus stock — see OrderNeeds.

import { getTranslations } from "next-intl/server";
import { OrderNeeds } from "@/components/module-4/order-needs";
import { canView, loadStockMasterPage } from "@/components/module-4/stockmaster-page-data";

export default async function Page() {
  const data = await loadStockMasterPage(canView("orderneeds"));
  if (!data) {
    const tErrors = await getTranslations("errors");
    return <p className="text-sm text-destructive">{tErrors("forbidden")}</p>;
  }

  return <OrderNeeds seasons={data.seasons} permissions={data.permissions} />;
}
