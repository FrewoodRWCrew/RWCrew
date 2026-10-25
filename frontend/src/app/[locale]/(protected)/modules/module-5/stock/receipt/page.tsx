// Atelier's "Stock > Ontvangst" screen — see StockBookingScreen (mode "receipt").

import { getTranslations } from "next-intl/server";
import { serverApiFetch } from "@/lib/server-api";
import type { AtelierStockArticle } from "@/lib/types";
import { StockBookingScreen } from "@/components/module-5/stock-booking-screen";
import { atelierCan, loadAtelierPage } from "@/components/module-5/atelier-page-data";

export default async function AtelierReceiptPage() {
  const data = await loadAtelierPage("receipt");
  if (!data) {
    const tErrors = await getTranslations("errors");
    return <p className="text-sm text-destructive">{tErrors("forbidden")}</p>;
  }

  const stock = await serverApiFetch<AtelierStockArticle[]>("/api/modules/module-5/stock");
  return (
    <StockBookingScreen mode="receipt" initialStock={stock} canBook={atelierCan(data.permissions, "receipt", "create")} />
  );
}
