// StockMaster's "Masterdata > Producten > Limieten" screen: one of the four
// lookup lists nested under Products — see ProductLimitManagement for the actual UI.

import { getTranslations } from "next-intl/server";
import { serverApiFetch } from "@/lib/server-api";
import type { ProductLimit } from "@/lib/types";
import { ProductLimitManagement } from "@/components/module-4/product-limit-management";
import { canView, loadStockMasterPage } from "@/components/module-4/stockmaster-page-data";

export default async function StockMasterProductLimitsPage() {
  const data = await loadStockMasterPage(canView("product-limits"));
  if (!data) {
    const tErrors = await getTranslations("errors");
    return <p className="text-sm text-destructive">{tErrors("forbidden")}</p>;
  }

  const productLimits = await serverApiFetch<ProductLimit[]>("/api/modules/module-4/product-limits");
  return <ProductLimitManagement initialProductLimits={productLimits} />;
}
