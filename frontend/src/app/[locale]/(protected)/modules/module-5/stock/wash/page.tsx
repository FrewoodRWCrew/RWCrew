// Atelier's "Stock > Wassen" screen — see StockBookingScreen (mode "wash").

import { getTranslations } from "next-intl/server";
import { serverApiFetch } from "@/lib/server-api";
import type { AtelierStockArticle } from "@/lib/types";
import { StockBookingScreen } from "@/components/module-5/stock-booking-screen";
import { atelierCan, loadAtelierPage } from "@/components/module-5/atelier-page-data";

export default async function AtelierWashPage() {
  const data = await loadAtelierPage("wash");
  if (!data) {
    const tErrors = await getTranslations("errors");
    return <p className="text-sm text-destructive">{tErrors("forbidden")}</p>;
  }

  const stock = await serverApiFetch<AtelierStockArticle[]>("/api/modules/module-5/stock");
  return (
    <StockBookingScreen mode="wash" initialStock={stock} canBook={atelierCan(data.permissions, "wash", "create")} />
  );
}
