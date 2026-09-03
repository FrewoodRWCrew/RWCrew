// TagScan's "Scanners" screen: a table of registered scanner devices with
// add/change/delete — see ScannerManagement for the actual UI.

import { getTranslations } from "next-intl/server";
import { ServerApiError, serverApiFetch } from "@/lib/server-api";
import type { ProductType, Scanner } from "@/lib/types";
import { ScannerManagement } from "@/components/module-1/scanner-management";

export default async function TagscanScannersPage() {
  const tErrors = await getTranslations("errors");

  let scanners: Scanner[] | null = null;
  let productTypes: ProductType[] = [];
  try {
    scanners = await serverApiFetch<Scanner[]>("/api/modules/module-1/scanners");
    // Powers the "Type" dropdown on the create/edit form — fetched
    // separately since a user might be able to manage scanners without
    // also being able to view MasterData's Type screen directly.
    productTypes = await serverApiFetch<ProductType[]>("/api/modules/module-9/product-types").catch(() => []);
  } catch (error) {
    if (error instanceof ServerApiError && error.status === 403) {
      return <p className="text-sm text-destructive">{tErrors("forbidden")}</p>;
    }
    throw error;
  }

  return <ScannerManagement initialScanners={scanners} productTypes={productTypes} />;
}
