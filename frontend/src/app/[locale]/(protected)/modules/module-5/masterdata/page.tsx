// "Masterdata" has no page of its own: it opens its first screen, Artikelen.

import { getLocale } from "next-intl/server";
import { redirect } from "@/i18n/navigation";

export default async function AtelierMasterdataPage() {
  redirect({ href: "/modules/module-5/masterdata/articles", locale: await getLocale() });
}
