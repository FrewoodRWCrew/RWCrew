// Altsien Select's "Instellingen > E-mails" screen — see MailSettingsScreen.
// Viewing needs "view" on altsienselect.mailtemplates; saving, the test mail
// and changing the CC list need "edit".

import { getTranslations } from "next-intl/server";
import { serverApiFetch } from "@/lib/server-api";
import type { AltsienSelectMyPermissions } from "@/lib/types";
import { MailSettingsScreen } from "@/components/module-8/mail-settings-screen";

const SCREEN = "altsienselect.mailtemplates";

export default async function AltsienSelectMailSettingsPage() {
  const permissions = await serverApiFetch<AltsienSelectMyPermissions>("/api/modules/module-8/me/permissions");
  if (!permissions.viewable_screen_keys.includes(SCREEN)) {
    const tErrors = await getTranslations("errors");
    return <p className="text-sm text-destructive">{tErrors("forbidden")}</p>;
  }

  return <MailSettingsScreen canEdit={permissions.editable_screen_keys.includes(SCREEN)} />;
}
