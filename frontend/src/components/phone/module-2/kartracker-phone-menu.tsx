// KarTracker's phone menu under the heading "ACTIES": KarScan, Kar Planning
// and Kar Map, each only when the user's role may view that screen.

import { List, Map as MapIcon, ScanLine, Zap } from "lucide-react";
import { getTranslations } from "next-intl/server";
import type { KarTrackerPhoneRights } from "@/components/phone/module-2/kartracker-phone-rights";
import { karTrackerPhoneRoutes } from "@/components/phone/module-2/kartracker-phone-routes";
import { PhoneMenuRow } from "@/components/phone/shared/phone-menu-row";
import { PhoneNotice } from "@/components/phone/shared/phone-notice";

const MODULE_KEY = "module-2";

export async function KarTrackerPhoneMenu({ rights }: { rights: KarTrackerPhoneRights }) {
  const [t, tPhone] = await Promise.all([getTranslations("karTracker"), getTranslations("karTracker.phone.menu")]);

  if (!rights.canViewActions && !rights.canViewPlanning && !rights.canViewMap) {
    return <PhoneNotice>{tPhone("noScreens")}</PhoneNotice>;
  }

  return (
    <section className="flex flex-col gap-3">
      <h2 className="flex items-center gap-2 text-xs font-semibold tracking-wide text-muted-foreground uppercase">
        <Zap className="size-4" />
        {t("actionsGroup")}
      </h2>
      {rights.canViewActions && (
        <PhoneMenuRow
          href={karTrackerPhoneRoutes.scan}
          icon={ScanLine}
          title={tPhone("karScanTitle")}
          description={tPhone("karScanDescription")}
          moduleKey={MODULE_KEY}
        />
      )}
      {rights.canViewPlanning && (
        <PhoneMenuRow
          href={karTrackerPhoneRoutes.planning}
          icon={List}
          title={t("karPlanning.title")}
          description={tPhone("planningDescription")}
          moduleKey={MODULE_KEY}
        />
      )}
      {rights.canViewMap && (
        <PhoneMenuRow
          href={karTrackerPhoneRoutes.map()}
          icon={MapIcon}
          title={t("karMap.title")}
          description={tPhone("mapDescription")}
          moduleKey={MODULE_KEY}
        />
      )}
    </section>
  );
}
