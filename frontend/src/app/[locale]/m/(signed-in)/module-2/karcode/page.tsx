// The Karcode Simulator on the phone: the same calculator as the web screen
// (scan the kar's QR code or type its number, get the code of its lock), for
// roles with "view" on kartracker.karcodesimulator.

import { getTranslations } from "next-intl/server";
import { KarcodeCalculator } from "@/components/module-2/karcode-calculator";
import { getKarTrackerPhoneRights } from "@/components/phone/module-2/kartracker-phone-rights";
import { karTrackerPhoneRoutes } from "@/components/phone/module-2/kartracker-phone-routes";
import { PhoneBody } from "@/components/phone/shared/phone-body";
import { PhoneHeader } from "@/components/phone/shared/phone-header";
import { PhoneNotice } from "@/components/phone/shared/phone-notice";

export default async function KarcodePhonePage() {
  const [t, tCommon, tErrors, rights] = await Promise.all([
    getTranslations("karTracker.karcodeSimulator"),
    getTranslations("common"),
    getTranslations("errors"),
    getKarTrackerPhoneRights(),
  ]);

  return (
    <>
      <PhoneHeader title={t("title")} backHref={karTrackerPhoneRoutes.menu} backLabel={tCommon("back")} moduleKey="module-2" />
      <PhoneBody>
        {rights?.canViewKarcode ? (
          <KarcodeCalculator variant="phone" />
        ) : (
          <PhoneNotice>{tErrors("forbidden")}</PhoneNotice>
        )}
      </PhoneBody>
    </>
  );
}
