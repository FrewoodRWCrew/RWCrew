// Visiting "Instellingen" itself just forwards to its only item, "Redenen".

import { getLocale } from "next-intl/server";
import { redirect } from "@/i18n/navigation";

export default async function SettingsPage() {
  redirect({ href: "/modules/module-4/settings/reasons", locale: await getLocale() });
}
