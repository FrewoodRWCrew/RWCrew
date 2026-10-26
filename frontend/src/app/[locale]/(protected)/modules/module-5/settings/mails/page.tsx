// Atelier's "Instellingen > E-mails" screen — see MailTemplatesScreen. Saving
// and sending a test mail need "edit" on atelier.mailtemplates.

import { getTranslations } from "next-intl/server";
import { MailTemplatesScreen } from "@/components/module-5/mail-templates-screen";
import { atelierCan, loadAtelierPage } from "@/components/module-5/atelier-page-data";

export default async function AtelierMailTemplatesPage() {
  const data = await loadAtelierPage("mailtemplates");
  if (!data) {
    const tErrors = await getTranslations("errors");
    return <p className="text-sm text-destructive">{tErrors("forbidden")}</p>;
  }

  return <MailTemplatesScreen canEdit={atelierCan(data.permissions, "mailtemplates", "edit")} />;
}
