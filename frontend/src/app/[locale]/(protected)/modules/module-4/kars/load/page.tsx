// StockMaster's "Kar laden": the loading overview of every kar, or the
// shared booking panel for one kar — see KarLoadScreen. Needs the right to
// make this booking.

import { getTranslations } from "next-intl/server";
import { KarLoadScreen } from "@/components/module-4/kar-load-screen";
import { canBook } from "@/components/module-4/stockmaster-common";
import { loadStockMasterPage } from "@/components/module-4/stockmaster-page-data";

export default async function Page() {
  const data = await loadStockMasterPage((permissions) => canBook(permissions, "kar_load"));
  if (!data) {
    const tErrors = await getTranslations("errors");
    return <p className="text-sm text-destructive">{tErrors("forbidden")}</p>;
  }

  return <KarLoadScreen seasons={data.seasons} permissions={data.permissions} />;
}
