// StockMaster's "Masterdata > Producten > Categorieën" screen: one of the four
// lookup lists nested under Products — see ProductCategoryManagement for the actual UI.

import { getTranslations } from "next-intl/server";
import { serverApiFetch } from "@/lib/server-api";
import type { ProductCategory } from "@/lib/types";
import { ProductCategoryManagement } from "@/components/module-4/product-category-management";
import { canView, loadStockMasterPage } from "@/components/module-4/stockmaster-page-data";

export default async function StockMasterProductCategoriesPage() {
  const data = await loadStockMasterPage(canView("product-categories"));
  if (!data) {
    const tErrors = await getTranslations("errors");
    return <p className="text-sm text-destructive">{tErrors("forbidden")}</p>;
  }

  const productCategories = await serverApiFetch<ProductCategory[]>("/api/modules/module-4/product-categories");
  return <ProductCategoryManagement initialProductCategories={productCategories} />;
}
