// Atelier's "Reservaties > Reservaties" screen — see ReservationScreen. The
// articles are loaded here for the package dialog and the chips.

import { getTranslations } from "next-intl/server";
import { serverApiFetch } from "@/lib/server-api";
import type { AtelierArticle } from "@/lib/types";
import { ReservationScreen } from "@/components/module-5/reservation-screen";
import { atelierCan, loadAtelierPage } from "@/components/module-5/atelier-page-data";

export default async function AtelierReservationsPage() {
  const data = await loadAtelierPage("reservations");
  if (!data) {
    const tErrors = await getTranslations("errors");
    return <p className="text-sm text-destructive">{tErrors("forbidden")}</p>;
  }

  const articles = await serverApiFetch<AtelierArticle[]>("/api/modules/module-5/articles");
  return (
    <ReservationScreen
      seasons={data.seasons}
      articles={articles}
      canEdit={atelierCan(data.permissions, "reservations", "edit")}
    />
  );
}
