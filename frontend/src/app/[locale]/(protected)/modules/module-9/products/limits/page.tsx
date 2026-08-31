// MasterData's "Limiet" screen: one of the three lookup lists nested under
// Products — see ProductLimitManagement for the actual UI.

import { getTranslations } from "next-intl/server";
import { ServerApiError, serverApiFetch } from "@/lib/server-api";
import type { ProductLimit } from "@/lib/types";
import { ProductLimitManagement } from "@/components/module-9/product-limit-management";

export default async function MasterDataProductLimitsPage() {
  const tErrors = await getTranslations("errors");

  let productLimits: ProductLimit[] | null = null;
  try {
    productLimits = await serverApiFetch<ProductLimit[]>("/api/modules/module-9/product-limits");
  } catch (error) {
    if (error instanceof ServerApiError && error.status === 403) {
      return <p className="text-sm text-destructive">{tErrors("forbidden")}</p>;
    }
    throw error;
  }

  return <ProductLimitManagement initialProductLimits={productLimits} />;
}
