// Atelier's "Stock > Stock" screen — see StockOverview.

import { getTranslations } from "next-intl/server";
import { serverApiFetch } from "@/lib/server-api";
import type { AtelierStockArticle } from "@/lib/types";
import { StockOverview } from "@/components/module-5/stock-overview";
import { loadAtelierPage } from "@/components/module-5/atelier-page-data";

export default async function AtelierStockPage() {
  const data = await loadAtelierPage("stock");
  if (!data) {
    const tErrors = await getTranslations("errors");
    return <p className="text-sm text-destructive">{tErrors("forbidden")}</p>;
  }

  const stock = await serverApiFetch<AtelierStockArticle[]>("/api/modules/module-5/stock");
  return <StockOverview articles={stock} />;
}
