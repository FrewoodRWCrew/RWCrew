// StockMaster's "Instellingen > Redenen" — see ReasonsManagement.

import { getTranslations } from "next-intl/server";
import { serverApiFetch } from "@/lib/server-api";
import type { StockMasterReason } from "@/lib/types";
import { ReasonsManagement } from "@/components/module-4/reasons-management";
import { canView, loadStockMasterPage } from "@/components/module-4/stockmaster-page-data";

export default async function ReasonsPage() {
  const data = await loadStockMasterPage(canView("reasons"));
  if (!data) {
    const tErrors = await getTranslations("errors");
    return <p className="text-sm text-destructive">{tErrors("forbidden")}</p>;
  }

  const reasons = await serverApiFetch<StockMasterReason[]>("/api/modules/module-4/reasons");
  return <ReasonsManagement initialReasons={reasons} permissions={data.permissions} />;
}
