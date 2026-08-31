// MasterData's "Magazijn" screen: one of the three lookup lists nested
// under Products — see WarehouseManagement for the actual UI.

import { getTranslations } from "next-intl/server";
import { ServerApiError, serverApiFetch } from "@/lib/server-api";
import type { Warehouse } from "@/lib/types";
import { WarehouseManagement } from "@/components/module-9/warehouse-management";

export default async function MasterDataWarehousesPage() {
  const tErrors = await getTranslations("errors");

  let warehouses: Warehouse[] | null = null;
  try {
    warehouses = await serverApiFetch<Warehouse[]>("/api/modules/module-9/warehouses");
  } catch (error) {
    if (error instanceof ServerApiError && error.status === 403) {
      return <p className="text-sm text-destructive">{tErrors("forbidden")}</p>;
    }
    throw error;
  }

  return <WarehouseManagement initialWarehouses={warehouses} />;
}
