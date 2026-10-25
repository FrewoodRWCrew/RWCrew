// Atelier's "Reservaties > Voorbereiden" screen — see PreparationScreen.

import { getTranslations } from "next-intl/server";
import { PreparationScreen } from "@/components/module-5/preparation-screen";
import { loadAtelierPage } from "@/components/module-5/atelier-page-data";

export default async function AtelierPreparationPage() {
  const data = await loadAtelierPage("preparation");
  if (!data) {
    const tErrors = await getTranslations("errors");
    return <p className="text-sm text-destructive">{tErrors("forbidden")}</p>;
  }

  return <PreparationScreen seasons={data.seasons} />;
}
