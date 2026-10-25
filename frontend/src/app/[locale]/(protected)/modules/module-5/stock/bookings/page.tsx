// Atelier's "Stock > Boekingen" screen — see StockBookings. Undoing a booking
// needs "edit" on atelier.bookings.

import { getTranslations } from "next-intl/server";
import { StockBookings } from "@/components/module-5/stock-bookings";
import { atelierCan, loadAtelierPage } from "@/components/module-5/atelier-page-data";

export default async function AtelierBookingsPage() {
  const data = await loadAtelierPage("bookings");
  if (!data) {
    const tErrors = await getTranslations("errors");
    return <p className="text-sm text-destructive">{tErrors("forbidden")}</p>;
  }

  return <StockBookings canUndo={atelierCan(data.permissions, "bookings", "edit")} />;
}
