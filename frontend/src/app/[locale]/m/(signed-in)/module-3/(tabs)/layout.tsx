// The module's two tabbed screens share one orange header (back to the
// tiles) and the tab bar at the bottom.

import { getTranslations } from "next-intl/server";
import { getInterventionRequestsPhoneRights } from "@/components/phone/module-3/intervention-requests-phone-rights";
import { InterventionRequestsPhoneTabs } from "@/components/phone/module-3/intervention-requests-phone-tabs";
import { PhoneHeader } from "@/components/phone/shared/phone-header";
import { PHONE_HOME_HREF } from "@/components/phone/shared/phone-modules";

export default async function InterventionRequestsTabsLayout({ children }: { children: React.ReactNode }) {
  const [t, tCommon, rights] = await Promise.all([
    getTranslations("interventionRequests"),
    getTranslations("common"),
    getInterventionRequestsPhoneRights(),
  ]);

  return (
    <>
      <PhoneHeader title={t("moduleTitle")} backHref={PHONE_HOME_HREF} backLabel={tCommon("back")} moduleKey="module-3" />
      <div className="flex flex-1 flex-col">{children}</div>
      <InterventionRequestsPhoneTabs showRequestsTab={rights?.canViewRequests ?? false} />
    </>
  );
}
