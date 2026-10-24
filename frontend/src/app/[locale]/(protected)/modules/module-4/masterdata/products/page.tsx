// StockMaster's "Masterdata > Producten" screen: a table of products with
// add/change/delete, matching the field set of the reference "Producten"
// edit screen (including the product picture) — see ProductsManagement for
// the actual UI.

import { getTranslations } from "next-intl/server";
import { serverApiFetch } from "@/lib/server-api";
import type { Product, ProductCategory, ProductLimit, ProductType, Warehouse } from "@/lib/types";
import { ProductsManagement } from "@/components/module-4/products-management";
import { canView, loadStockMasterPage } from "@/components/module-4/stockmaster-page-data";

export default async function StockMasterProductsPage() {
  const data = await loadStockMasterPage(canView("products"));
  if (!data) {
    const tErrors = await getTranslations("errors");
    return <p className="text-sm text-destructive">{tErrors("forbidden")}</p>;
  }

  // These four lookup lists power the Type/Magazijn/Categorie/Limiet
  // dropdowns on the create/edit form — fetched here too since a user might
  // be able to manage products without also being able to view those
  // screens directly.
  const [products, productTypes, warehouses, productCategories, productLimits] = await Promise.all([
    serverApiFetch<Product[]>("/api/modules/module-4/products"),
    serverApiFetch<ProductType[]>("/api/modules/module-4/product-types").catch(() => []),
    serverApiFetch<Warehouse[]>("/api/modules/module-4/warehouses").catch(() => []),
    serverApiFetch<ProductCategory[]>("/api/modules/module-4/product-categories").catch(() => []),
    serverApiFetch<ProductLimit[]>("/api/modules/module-4/product-limits").catch(() => []),
  ]);

  return (
    <ProductsManagement
      initialProducts={products}
      productTypes={productTypes}
      warehouses={warehouses}
      productCategories={productCategories}
      productLimits={productLimits}
    />
  );
}
