// KarTracker's phone menu: one row per phone screen the user may see.

import { getTranslations } from "next-intl/server";
import { getKarTrackerPhoneRights } from "@/components/phone/module-2/kartracker-phone-rights";
import { KarTrackerPhoneMenu } from "@/components/phone/module-2/kartracker-phone-menu";
import { PhoneBody } from "@/components/phone/shared/phone-body";
import { PhoneHeader } from "@/components/phone/shared/phone-header";
import { PHONE_HOME_HREF } from "@/components/phone/shared/phone-modules";

export default async function KarTrackerPhoneMenuPage() {
  const [t, tCommon, rights] = await Promise.all([
    getTranslations("karTracker"),
    getTranslations("common"),
    getKarTrackerPhoneRights(),
  ]);

  return (
    <>
      <PhoneHeader
        title={t("moduleTitle")}
        backHref={PHONE_HOME_HREF}
        backLabel={tCommon("back")}
        moduleKey="module-2"
      />
      <PhoneBody>{rights && <KarTrackerPhoneMenu rights={rights} />}</PhoneBody>
    </>
  );
}
