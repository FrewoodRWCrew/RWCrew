// A new intervention request, opened with the "+" on the Akties list.

import { getTranslations } from "next-intl/server";
import { serverApiFetch } from "@/lib/server-api";
import type { InterventionRequestsLookups } from "@/lib/types";
import { getInterventionRequestsPhoneRights } from "@/components/phone/module-3/intervention-requests-phone-rights";
import { interventionRequestsPhoneRoutes } from "@/components/phone/module-3/intervention-requests-phone-routes";
import { RequestForm } from "@/components/phone/module-3/request-form";
import { PhoneBody } from "@/components/phone/shared/phone-body";
import { PhoneHeader } from "@/components/phone/shared/phone-header";
import { PhoneNotice } from "@/components/phone/shared/phone-notice";

export default async function NewRequestPage() {
  const [t, tCommon, tErrors, rights] = await Promise.all([
    getTranslations("interventionRequests.requests"),
    getTranslations("common"),
    getTranslations("errors"),
    getInterventionRequestsPhoneRights(),
  ]);
  const canCreate = (rights?.canViewRequests && rights.canCreateRequests) ?? false;
  const lookups = canCreate ? await serverApiFetch<InterventionRequestsLookups>("/api/modules/module-3/lookups") : null;

  return (
    <>
      <PhoneHeader
        title={t("newRequest")}
        backHref={interventionRequestsPhoneRoutes.requests}
        backLabel={tCommon("back")}
        moduleKey="module-3"
      />
      <PhoneBody>
        {lookups ? <RequestForm lookups={lookups} canSave /> : <PhoneNotice>{tErrors("forbidden")}</PhoneNotice>}
      </PhoneBody>
    </>
  );
}
