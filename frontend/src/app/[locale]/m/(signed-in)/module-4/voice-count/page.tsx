// The voice count ("Spraaktelling"): scan a kar's QR code, choose Ophalen or
// Terugbrengen, say what is there and save it.

import { getTranslations } from "next-intl/server";
import { serverApiFetch } from "@/lib/server-api";
import type { StockMasterVoiceCountLookups } from "@/lib/types";
import { getStockMasterPhoneRights } from "@/components/phone/module-4/stockmaster-phone-rights";
import { stockMasterPhoneRoutes } from "@/components/phone/module-4/stockmaster-phone-routes";
import { VoiceCountScreen } from "@/components/phone/module-4/voice-count-screen";
import { PhoneBody } from "@/components/phone/shared/phone-body";
import { PhoneHeader } from "@/components/phone/shared/phone-header";
import { PhoneNotice } from "@/components/phone/shared/phone-notice";

export default async function VoiceCountPage() {
  const [t, tCommon, rights] = await Promise.all([
    getTranslations("stockMaster.phone"),
    getTranslations("common"),
    getStockMasterPhoneRights(),
  ]);
  // The kars and products to recognise (only fetched when allowed).
  const lookups = rights?.canVoiceCount
    ? await serverApiFetch<StockMasterVoiceCountLookups>("/api/modules/module-4/voice-count/lookups")
    : null;

  return (
    <>
      <PhoneHeader
        title={t("menu.voiceCountTitle")}
        backHref={stockMasterPhoneRoutes.menu}
        backLabel={tCommon("back")}
        moduleKey="module-4"
      />
      <PhoneBody>{lookups ? <VoiceCountScreen lookups={lookups} /> : <PhoneNotice>{t("noRights")}</PhoneNotice>}</PhoneBody>
    </>
  );
}
