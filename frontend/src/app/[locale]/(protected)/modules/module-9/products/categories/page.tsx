// MasterData's "Categorie" screen: one of the four lookup lists nested
// under Products — see ProductCategoryManagement for the actual UI.

import { getTranslations } from "next-intl/server";
import { ServerApiError, serverApiFetch } from "@/lib/server-api";
import type { ProductCategory } from "@/lib/types";
import { ProductCategoryManagement } from "@/components/module-9/product-category-management";

export default async function MasterDataProductCategoriesPage() {
  const tErrors = await getTranslations("errors");

  let productCategories: ProductCategory[] | null = null;
  try {
    productCategories = await serverApiFetch<ProductCategory[]>("/api/modules/module-9/product-categories");
  } catch (error) {
    if (error instanceof ServerApiError && error.status === 403) {
      return <p className="text-sm text-destructive">{tErrors("forbidden")}</p>;
    }
    throw error;
  }

  return <ProductCategoryManagement initialProductCategories={productCategories} />;
}
