// Atelier's "Balie > Openstaand" screen — see OpenHandouts.

import { getTranslations } from "next-intl/server";
import { OpenHandouts } from "@/components/module-5/open-handouts";
import { loadAtelierPage } from "@/components/module-5/atelier-page-data";

export default async function AtelierOpenHandoutsPage() {
  const data = await loadAtelierPage("open");
  if (!data) {
    const tErrors = await getTranslations("errors");
    return <p className="text-sm text-destructive">{tErrors("forbidden")}</p>;
  }

  return <OpenHandouts seasons={data.seasons} />;
}
