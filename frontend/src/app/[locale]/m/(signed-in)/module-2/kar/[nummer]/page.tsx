// One kar after scanning it: its number and ploeg, the movement form (new
// status + automatic GPS position) and its last 5 movements.

import { notFound } from "next/navigation";
import { getTranslations } from "next-intl/server";
import { serverApiFetch } from "@/lib/server-api";
import type { KarTrackerKarAction, KarTrackerKarActionLookups } from "@/lib/types";
import { KarMovementForm } from "@/components/phone/module-2/kar-movement-form";
import { KarRecentActions } from "@/components/phone/module-2/kar-recent-actions";
import { getKarTrackerPhoneRights } from "@/components/phone/module-2/kartracker-phone-rights";
import { karTrackerPhoneRoutes } from "@/components/phone/module-2/kartracker-phone-routes";
import { PhoneBody } from "@/components/phone/shared/phone-body";
import { PhoneHeader } from "@/components/phone/shared/phone-header";
import { PhoneNotice } from "@/components/phone/shared/phone-notice";

// How many of the kar's latest movements are listed under the form.
const RECENT_ACTIONS_LIMIT = 5;

/** The kar number from the URL; tolerant of it arriving still encoded. */
function decodeKarNummer(value: string): string {
  try {
    return decodeURIComponent(value);
  } catch {
    return value;
  }
}

export default async function KarPage({ params }: { params: Promise<{ nummer: string }> }) {
  const karNummer = decodeKarNummer((await params).nummer).trim().toLowerCase();
  const [t, tCommon, rights] = await Promise.all([
    getTranslations("karTracker.phone"),
    getTranslations("common"),
    getKarTrackerPhoneRights(),
  ]);

  const header = (title: string) => (
    <PhoneHeader title={title} backHref={karTrackerPhoneRoutes.scan} backLabel={tCommon("back")} moduleKey="module-2" />
  );

  if (!rights?.canViewActions) {
    return (
      <>
        {header(t("kar.title", { kar: karNummer }))}
        <PhoneBody>
          <PhoneNotice>{t("noActionsRights")}</PhoneNotice>
        </PhoneBody>
      </>
    );
  }

  // Find the kar (same trimmed, case-insensitive match as the scanner).
  const lookups = await serverApiFetch<KarTrackerKarActionLookups>("/api/modules/module-2/kar-actions/lookups");
  const kar = lookups.karren.find((candidate) => candidate.kar_nummer.trim().toLowerCase() === karNummer);
  if (!kar) notFound();

  const recentActions = await serverApiFetch<KarTrackerKarAction[]>(
    `/api/modules/module-2/kar-actions?kar_id=${kar.id}&limit=${RECENT_ACTIONS_LIMIT}`,
  );

  return (
    <>
      {header(t("kar.title", { kar: kar.kar_nummer }))}
      <PhoneBody>
        {/* The kar itself, read-only. */}
        <div className="grid grid-cols-2 gap-3 rounded-xl border bg-card p-4">
          <div>
            <p className="text-xs text-muted-foreground">{t("kar.karLabel")}</p>
            <p className="text-2xl font-bold">{kar.kar_nummer}</p>
          </div>
          <div>
            <p className="text-xs text-muted-foreground">{t("kar.teamLabel")}</p>
            <p className="font-medium">{kar.team_name ?? t("kar.noTeam")}</p>
          </div>
        </div>

        {rights.canCreateActions ? (
          <KarMovementForm kar={kar} statuses={lookups.statuses} />
        ) : (
          <PhoneNotice>{t("kar.noCreateRights")}</PhoneNotice>
        )}

        <KarRecentActions actions={recentActions} />
      </PhoneBody>
    </>
  );
}
