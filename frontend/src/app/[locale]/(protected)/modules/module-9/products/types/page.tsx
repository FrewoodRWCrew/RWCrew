// MasterData's "Type" screen: one of the three lookup lists nested under
// Products — see ProductTypeManagement for the actual UI.

import { getTranslations } from "next-intl/server";
import { ServerApiError, serverApiFetch } from "@/lib/server-api";
import type { ProductType } from "@/lib/types";
import { ProductTypeManagement } from "@/components/module-9/product-type-management";

export default async function MasterDataProductTypesPage() {
  const tErrors = await getTranslations("errors");

  let productTypes: ProductType[] | null = null;
  try {
    productTypes = await serverApiFetch<ProductType[]>("/api/modules/module-9/product-types");
  } catch (error) {
    if (error instanceof ServerApiError && error.status === 403) {
      return <p className="text-sm text-destructive">{tErrors("forbidden")}</p>;
    }
    throw error;
  }

  return <ProductTypeManagement initialProductTypes={productTypes} />;
}
