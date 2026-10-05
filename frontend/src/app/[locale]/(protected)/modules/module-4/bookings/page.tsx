// StockMaster's "Boekingen": the booking history — see BookingsList.

import { getTranslations } from "next-intl/server";
import { BookingsList } from "@/components/module-4/bookings-list";
import { canView, loadStockMasterPage } from "@/components/module-4/stockmaster-page-data";

export default async function Page() {
  const data = await loadStockMasterPage(canView("bookings"));
  if (!data) {
    const tErrors = await getTranslations("errors");
    return <p className="text-sm text-destructive">{tErrors("forbidden")}</p>;
  }

  return <BookingsList seasons={data.seasons} />;
}
