// Interventie Aanvragen on the phone. Like the desktop module layout, it
// first checks that the user may open the module at all. The two tabs
// (Akties, KPI overzicht) live in (tabs)/; the request form pages sit next
// to them, without the tab bar.

import { getTranslations } from "next-intl/server";
import { getModuleAccentStyle } from "@/lib/module-theme";
import { getInterventionRequestsPhoneRights } from "@/components/phone/module-3/intervention-requests-phone-rights";
import { PhoneForbidden } from "@/components/phone/shared/phone-forbidden";

export default async function InterventionRequestsPhoneLayout({ children }: { children: React.ReactNode }) {
  const [t, rights] = await Promise.all([
    getTranslations("interventionRequests"),
    getInterventionRequestsPhoneRights(),
  ]);

  if (rights === null) {
    return <PhoneForbidden title={t("moduleTitle")} />;
  }

  // The module's orange becomes the "primary" colour of every button inside.
  return (
    <div className="flex flex-1 flex-col" style={getModuleAccentStyle("module-3")}>
      {children}
    </div>
  );
}
