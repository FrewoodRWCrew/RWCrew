// StockMaster's phone menu: one row per phone screen the user may see
// (for now only the voice count).

import { Mic, Zap } from "lucide-react";
import { getTranslations } from "next-intl/server";
import type { StockMasterPhoneRights } from "@/components/phone/module-4/stockmaster-phone-rights";
import { stockMasterPhoneRoutes } from "@/components/phone/module-4/stockmaster-phone-routes";
import { PhoneMenuRow } from "@/components/phone/shared/phone-menu-row";
import { PhoneNotice } from "@/components/phone/shared/phone-notice";

const MODULE_KEY = "module-4";

export async function StockMasterPhoneMenu({ rights }: { rights: StockMasterPhoneRights }) {
  const t = await getTranslations("stockMaster.phone.menu");

  if (!rights.canVoiceCount) {
    return <PhoneNotice>{t("noScreens")}</PhoneNotice>;
  }

  return (
    <section className="flex flex-col gap-3">
      <h2 className="flex items-center gap-2 text-xs font-semibold tracking-wide text-muted-foreground uppercase">
        <Zap className="size-4" />
        {t("actionsGroup")}
      </h2>
      <PhoneMenuRow
        href={stockMasterPhoneRoutes.voiceCount}
        icon={Mic}
        title={t("voiceCountTitle")}
        description={t("voiceCountDescription")}
        moduleKey={MODULE_KEY}
      />
    </section>
  );
}
