// Kar Map on the phone: Karren, Afleverlocaties and Distributiepunten on the
// same map as the desktop. "?focus=kar-12" (from Kar Planning's "Toon op
// kaart") flies to that pin on opening.

import { getTranslations } from "next-intl/server";
import { serverApiFetch } from "@/lib/server-api";
import type { KarTrackerGroundplan, KarTrackerKarMapResponse } from "@/lib/types";
import { KarMapPhone } from "@/components/phone/module-2/kar-map-phone";
import { getKarTrackerPhoneRights } from "@/components/phone/module-2/kartracker-phone-rights";
import { karTrackerPhoneRoutes } from "@/components/phone/module-2/kartracker-phone-routes";
import { PhoneBody } from "@/components/phone/shared/phone-body";
import { PhoneHeader } from "@/components/phone/shared/phone-header";
import { PhoneNotice } from "@/components/phone/shared/phone-notice";

export default async function KarMapPage({ searchParams }: { searchParams: Promise<{ focus?: string }> }) {
  const [{ focus }, t, tCommon, tErrors, rights] = await Promise.all([
    searchParams,
    getTranslations("karTracker.karMap"),
    getTranslations("common"),
    getTranslations("errors"),
    getKarTrackerPhoneRights(),
  ]);

  const header = (
    <PhoneHeader title={t("title")} backHref={karTrackerPhoneRoutes.menu} backLabel={tCommon("back")} moduleKey="module-2" />
  );

  if (!rights?.canViewMap) {
    return (
      <>
        {header}
        <PhoneBody>
          <PhoneNotice>{tErrors("forbidden")}</PhoneNotice>
        </PhoneBody>
      </>
    );
  }

  const [data, groundplans] = await Promise.all([
    serverApiFetch<KarTrackerKarMapResponse>("/api/modules/module-2/kar-map"),
    serverApiFetch<KarTrackerGroundplan[]>("/api/modules/module-2/groundplans"),
  ]);

  // The map fills the rest of the screen, so no padded body here.
  return (
    <>
      {header}
      <KarMapPhone data={data} groundplans={groundplans} focusKey={focus} />
    </>
  );
}
