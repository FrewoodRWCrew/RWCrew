// KarScan: the phone version of "Manuele kar beweging". Scanning the QR code
// on a kar opens that kar's movement form.

import { getTranslations } from "next-intl/server";
import { serverApiFetch } from "@/lib/server-api";
import type { KarTrackerKarActionLookups } from "@/lib/types";
import { KarScan } from "@/components/phone/module-2/kar-scan";
import { getKarTrackerPhoneRights } from "@/components/phone/module-2/kartracker-phone-rights";
import { karTrackerPhoneRoutes } from "@/components/phone/module-2/kartracker-phone-routes";
import { PhoneBody } from "@/components/phone/shared/phone-body";
import { PhoneHeader } from "@/components/phone/shared/phone-header";
import { PhoneNotice } from "@/components/phone/shared/phone-notice";

export default async function KarScanPage() {
  const [t, tCommon, rights] = await Promise.all([
    getTranslations("karTracker.phone"),
    getTranslations("common"),
    getKarTrackerPhoneRights(),
  ]);
  const canView = rights?.canViewActions ?? false;
  // The kar list, to match a scanned number against (only fetched when allowed).
  const lookups = canView
    ? await serverApiFetch<KarTrackerKarActionLookups>("/api/modules/module-2/kar-actions/lookups")
    : null;

  return (
    <>
      <PhoneHeader
        title={t("menu.karScanTitle")}
        backHref={karTrackerPhoneRoutes.menu}
        backLabel={tCommon("back")}
        moduleKey="module-2"
      />
      <PhoneBody>
        {lookups ? <KarScan karren={lookups.karren} /> : <PhoneNotice>{t("noActionsRights")}</PhoneNotice>}
      </PhoneBody>
    </>
  );
}
