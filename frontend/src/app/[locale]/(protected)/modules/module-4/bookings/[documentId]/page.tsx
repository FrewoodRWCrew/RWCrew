// One StockMaster booking with its lines, PDF and "Ongedaan maken" — see
// BookingDetail.

import { getTranslations } from "next-intl/server";
import { notFound } from "next/navigation";
import { ServerApiError, serverApiFetch } from "@/lib/server-api";
import type { StockMasterDocument } from "@/lib/types";
import { BookingDetail } from "@/components/module-4/booking-detail";
import { canView, loadStockMasterPage } from "@/components/module-4/stockmaster-page-data";

interface BookingPageProps {
  params: Promise<{ documentId: string }>;
}

export default async function BookingPage({ params }: BookingPageProps) {
  const { documentId } = await params;
  const id = Number(documentId);
  if (!Number.isInteger(id) || id <= 0) notFound();

  const data = await loadStockMasterPage(canView("bookings"));
  if (!data) {
    const tErrors = await getTranslations("errors");
    return <p className="text-sm text-destructive">{tErrors("forbidden")}</p>;
  }

  let document: StockMasterDocument;
  try {
    document = await serverApiFetch<StockMasterDocument>(`/api/modules/module-4/bookings/${id}`);
  } catch (error) {
    if (error instanceof ServerApiError && error.status === 404) notFound();
    throw error;
  }

  // The key makes the screen start fresh when undoing jumps to the reversal.
  return <BookingDetail key={document.id} document={document} permissions={data.permissions} />;
}
