// MasterData's "Products" screen: a table of products with add/change/
// delete, matching the field set of the reference "Producten" edit
// screen (minus image upload, a later step) — see ProductsManagement for
// the actual UI.

import { getTranslations } from "next-intl/server";
import { ServerApiError, serverApiFetch } from "@/lib/server-api";
import type { Product, ProductCategory, ProductLimit, ProductType, Warehouse } from "@/lib/types";
import { ProductsManagement } from "@/components/module-9/products-management";

export default async function MasterDataProductsPage() {
  const tErrors = await getTranslations("errors");

  let products: Product[] | null = null;
  let productTypes: ProductType[] = [];
  let warehouses: Warehouse[] = [];
  let productCategories: ProductCategory[] = [];
  let productLimits: ProductLimit[] = [];
  try {
    products = await serverApiFetch<Product[]>("/api/modules/module-9/products");
    // These four lookup lists power the Type/Magazijn/Categorie/Limiet
    // dropdowns on the create/edit form — fetched here too since a user
    // might be able to manage products without also being able to view
    // those screens directly.
    [productTypes, warehouses, productCategories, productLimits] = await Promise.all([
      serverApiFetch<ProductType[]>("/api/modules/module-9/product-types").catch(() => []),
      serverApiFetch<Warehouse[]>("/api/modules/module-9/warehouses").catch(() => []),
      serverApiFetch<ProductCategory[]>("/api/modules/module-9/product-categories").catch(() => []),
      serverApiFetch<ProductLimit[]>("/api/modules/module-9/product-limits").catch(() => []),
    ]);
  } catch (error) {
    if (error instanceof ServerApiError && error.status === 403) {
      return <p className="text-sm text-destructive">{tErrors("forbidden")}</p>;
    }
    throw error;
  }

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
