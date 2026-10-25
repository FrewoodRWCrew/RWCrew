// Atelier's "Instellingen" screen — see AtelierSettingsScreen.

import { getTranslations } from "next-intl/server";
import { AtelierSettingsScreen } from "@/components/module-5/atelier-settings";
import { atelierCan, loadAtelierPage } from "@/components/module-5/atelier-page-data";

export default async function AtelierSettingsPage() {
  const data = await loadAtelierPage("settings");
  if (!data) {
    const tErrors = await getTranslations("errors");
    return <p className="text-sm text-destructive">{tErrors("forbidden")}</p>;
  }

  return <AtelierSettingsScreen canEdit={atelierCan(data.permissions, "settings", "edit")} />;
}
