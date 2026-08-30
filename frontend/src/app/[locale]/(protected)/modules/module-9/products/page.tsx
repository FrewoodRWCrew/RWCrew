// MasterData's "Products" screen: a table of products with add/change/
// delete, matching the field set of the reference "Producten" edit
// screen (minus image upload, a later step) — see ProductsManagement for
// the actual UI.

import { getTranslations } from "next-intl/server";
import { ServerApiError, serverApiFetch } from "@/lib/server-api";
import type { Product } from "@/lib/types";
import { ProductsManagement } from "@/components/module-9/products-management";

export default async function MasterDataProductsPage() {
  const tErrors = await getTranslations("errors");

  let products: Product[] | null = null;
  try {
    products = await serverApiFetch<Product[]>("/api/modules/module-9/products");
  } catch (error) {
    if (error instanceof ServerApiError && error.status === 403) {
      return <p className="text-sm text-destructive">{tErrors("forbidden")}</p>;
    }
    throw error;
  }

  return <ProductsManagement initialProducts={products} />;
}
