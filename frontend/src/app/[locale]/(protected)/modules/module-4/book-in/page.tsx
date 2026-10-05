// StockMaster's "Inboeken": the shared booking panel, pre-set for this
// action — see BookingPanel. Needs the right to make this booking.

import { getTranslations } from "next-intl/server";
import { BookingPanel } from "@/components/module-4/booking-panel";
import { canBook } from "@/components/module-4/stockmaster-common";
import { loadStockMasterPage } from "@/components/module-4/stockmaster-page-data";

export default async function Page() {
  const data = await loadStockMasterPage((permissions) => canBook(permissions, "book_in"));
  if (!data) {
    const tErrors = await getTranslations("errors");
    return <p className="text-sm text-destructive">{tErrors("forbidden")}</p>;
  }

  return <BookingPanel action="book_in" seasons={data.seasons} permissions={data.permissions} />;
}
