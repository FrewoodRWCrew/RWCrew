// Atelier's "Stock > Telling" screen — see StockCount.

import { getTranslations } from "next-intl/server";
import { serverApiFetch } from "@/lib/server-api";
import type { AtelierStockArticle } from "@/lib/types";
import { StockCount } from "@/components/module-5/stock-count";
import { atelierCan, loadAtelierPage } from "@/components/module-5/atelier-page-data";

export default async function AtelierCountPage() {
  const data = await loadAtelierPage("count");
  if (!data) {
    const tErrors = await getTranslations("errors");
    return <p className="text-sm text-destructive">{tErrors("forbidden")}</p>;
  }

  const stock = await serverApiFetch<AtelierStockArticle[]>("/api/modules/module-5/stock");
  return <StockCount initialStock={stock} canBook={atelierCan(data.permissions, "count", "create")} />;
}
