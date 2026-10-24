// StockMaster's "Masterdata > Producten > Type" screen: one of the four
// lookup lists nested under Products — see ProductTypeManagement for the actual UI.

import { getTranslations } from "next-intl/server";
import { serverApiFetch } from "@/lib/server-api";
import type { ProductType } from "@/lib/types";
import { ProductTypeManagement } from "@/components/module-4/product-type-management";
import { canView, loadStockMasterPage } from "@/components/module-4/stockmaster-page-data";

export default async function StockMasterProductTypesPage() {
  const data = await loadStockMasterPage(canView("product-types"));
  if (!data) {
    const tErrors = await getTranslations("errors");
    return <p className="text-sm text-destructive">{tErrors("forbidden")}</p>;
  }

  const productTypes = await serverApiFetch<ProductType[]>("/api/modules/module-4/product-types");
  return <ProductTypeManagement initialProductTypes={productTypes} />;
}
