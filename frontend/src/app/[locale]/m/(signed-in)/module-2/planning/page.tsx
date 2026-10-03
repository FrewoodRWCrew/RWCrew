// Kar Planning on the phone: every kar as a card, with its planned
// afleverlocatie per festival of the chosen season. Read-only, no printing.

import { getTranslations } from "next-intl/server";
import { serverApiFetch } from "@/lib/server-api";
import type { KarTrackerKarPlanningReport, KarTrackerSeasonOption } from "@/lib/types";
import { KarPlanningList } from "@/components/phone/module-2/kar-planning-list";
import { getKarTrackerPhoneRights } from "@/components/phone/module-2/kartracker-phone-rights";
import { karTrackerPhoneRoutes } from "@/components/phone/module-2/kartracker-phone-routes";
import { PhoneBody } from "@/components/phone/shared/phone-body";
import { PhoneHeader } from "@/components/phone/shared/phone-header";
import { PhoneNotice } from "@/components/phone/shared/phone-notice";

export default async function KarPlanningPage() {
  const [t, tCommon, tErrors, rights] = await Promise.all([
    getTranslations("karTracker.karPlanning"),
    getTranslations("common"),
    getTranslations("errors"),
    getKarTrackerPhoneRights(),
  ]);

  let content: React.ReactNode;
  if (!rights?.canViewPlanning) {
    content = <PhoneNotice>{tErrors("forbidden")}</PhoneNotice>;
  } else {
    // The open seasons (newest first); the newest one is shown first.
    const seasons = await serverApiFetch<KarTrackerSeasonOption[]>("/api/modules/module-2/seasons");
    const initialSeasonId = seasons[0]?.id ?? null;
    const query = initialSeasonId !== null ? `?season_id=${initialSeasonId}` : "";
    const initialReport = await serverApiFetch<KarTrackerKarPlanningReport>(`/api/modules/module-2/kar-planning${query}`);
    content = (
      <KarPlanningList
        seasons={seasons}
        initialSeasonId={initialSeasonId}
        initialReport={initialReport}
        canViewMap={rights.canViewMap}
      />
    );
  }

  return (
    <>
      <PhoneHeader title={t("title")} backHref={karTrackerPhoneRoutes.menu} backLabel={tCommon("back")} moduleKey="module-2" />
      <PhoneBody>{content}</PhoneBody>
    </>
  );
}
