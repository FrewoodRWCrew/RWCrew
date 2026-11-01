// Atelier's "Balie > Openstaand" screen — see OpenHandouts. Its Inname button
// reads with "view" on atelier.desk and books with "create" there; cancelling
// a pick-up in that dialog needs "edit".

import { getTranslations } from "next-intl/server";
import { OpenHandouts } from "@/components/module-5/open-handouts";
import { atelierCan, loadAtelierPage } from "@/components/module-5/atelier-page-data";

export default async function AtelierOpenHandoutsPage() {
  const data = await loadAtelierPage("open");
  if (!data) {
    const tErrors = await getTranslations("errors");
    return <p className="text-sm text-destructive">{tErrors("forbidden")}</p>;
  }

  return (
    <OpenHandouts
      seasons={data.seasons}
      canBook={data.permissions.viewable_screen_keys.includes("atelier.desk") && atelierCan(data.permissions, "desk", "create")}
      canCancel={atelierCan(data.permissions, "desk", "edit")}
    />
  );
}
