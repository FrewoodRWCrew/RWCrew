// StockMaster's phone menu: one row per phone screen the user may see.

import { getTranslations } from "next-intl/server";
import { getStockMasterPhoneRights } from "@/components/phone/module-4/stockmaster-phone-rights";
import { StockMasterPhoneMenu } from "@/components/phone/module-4/stockmaster-phone-menu";
import { PhoneBody } from "@/components/phone/shared/phone-body";
import { PhoneHeader } from "@/components/phone/shared/phone-header";
import { PHONE_HOME_HREF } from "@/components/phone/shared/phone-modules";

export default async function StockMasterPhoneMenuPage() {
  const [t, tCommon, rights] = await Promise.all([
    getTranslations("stockMaster"),
    getTranslations("common"),
    getStockMasterPhoneRights(),
  ]);

  return (
    <>
      <PhoneHeader title={t("moduleTitle")} backHref={PHONE_HOME_HREF} backLabel={tCommon("back")} moduleKey="module-4" />
      <PhoneBody>{rights && <StockMasterPhoneMenu rights={rights} />}</PhoneBody>
    </>
  );
}
