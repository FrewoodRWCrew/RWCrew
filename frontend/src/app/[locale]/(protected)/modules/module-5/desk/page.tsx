// Atelier's "Balie > Uitgifte & inname" screen — see DeskScreen. Booking a
// pick-up or return needs "create" on atelier.desk; cancelling a pick-up "edit".

import { getTranslations } from "next-intl/server";
import { DeskScreen } from "@/components/module-5/desk-screen";
import { atelierCan, loadAtelierPage } from "@/components/module-5/atelier-page-data";

export default async function AtelierDeskPage() {
  const data = await loadAtelierPage("desk");
  if (!data) {
    const tErrors = await getTranslations("errors");
    return <p className="text-sm text-destructive">{tErrors("forbidden")}</p>;
  }

  return (
    <DeskScreen
      seasons={data.seasons}
      canBook={atelierCan(data.permissions, "desk", "create")}
      canCancel={atelierCan(data.permissions, "desk", "edit")}
    />
  );
}
