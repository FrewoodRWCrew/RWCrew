// StockMaster's "Historiek > Tag-historiek" screen — see StockMasterTagHistory.

import { Suspense } from "react";
import { getTranslations } from "next-intl/server";
import { StockMasterTagHistory } from "@/components/module-4/tag-history";
import { canView, loadStockMasterPage } from "@/components/module-4/stockmaster-page-data";

export default async function Page() {
  const data = await loadStockMasterPage(canView("taghistory"));
  if (!data) {
    const tErrors = await getTranslations("errors");
    return <p className="text-sm text-destructive">{tErrors("forbidden")}</p>;
  }

  // The screen reads ?epc= from the URL (useSearchParams needs a Suspense boundary).
  return (
    <Suspense>
      <StockMasterTagHistory />
    </Suspense>
  );
}
