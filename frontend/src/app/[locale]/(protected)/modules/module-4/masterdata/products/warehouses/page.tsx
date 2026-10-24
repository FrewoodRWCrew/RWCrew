// StockMaster's "Masterdata > Producten > Magazijnen" screen: one of the four
// lookup lists nested under Products — see WarehouseManagement for the actual UI.

import { getTranslations } from "next-intl/server";
import { serverApiFetch } from "@/lib/server-api";
import type { Warehouse } from "@/lib/types";
import { WarehouseManagement } from "@/components/module-4/warehouse-management";
import { canView, loadStockMasterPage } from "@/components/module-4/stockmaster-page-data";

export default async function StockMasterWarehousesPage() {
  const data = await loadStockMasterPage(canView("warehouses"));
  if (!data) {
    const tErrors = await getTranslations("errors");
    return <p className="text-sm text-destructive">{tErrors("forbidden")}</p>;
  }

  const warehouses = await serverApiFetch<Warehouse[]>("/api/modules/module-4/warehouses");
  return <WarehouseManagement initialWarehouses={warehouses} />;
}
