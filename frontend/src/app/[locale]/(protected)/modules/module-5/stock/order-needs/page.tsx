// Atelier's "Stock > Te bestellen" screen — see OrderNeeds.

import { getTranslations } from "next-intl/server";
import { OrderNeeds } from "@/components/module-5/order-needs";
import { loadAtelierPage } from "@/components/module-5/atelier-page-data";

export default async function AtelierOrderNeedsPage() {
  const data = await loadAtelierPage("orderneeds");
  if (!data) {
    const tErrors = await getTranslations("errors");
    return <p className="text-sm text-destructive">{tErrors("forbidden")}</p>;
  }

  return <OrderNeeds seasons={data.seasons} />;
}
