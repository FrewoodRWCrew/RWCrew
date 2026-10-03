// One existing intervention request, opened from the Akties list: editable
// with the "edit" right, otherwise read-only.

import { notFound } from "next/navigation";
import { getTranslations } from "next-intl/server";
import { ServerApiError, serverApiFetch } from "@/lib/server-api";
import type { InterventionRequest, InterventionRequestsLookups } from "@/lib/types";
import { getInterventionRequestsPhoneRights } from "@/components/phone/module-3/intervention-requests-phone-rights";
import { interventionRequestsPhoneRoutes } from "@/components/phone/module-3/intervention-requests-phone-routes";
import { RequestForm } from "@/components/phone/module-3/request-form";
import { PhoneBody } from "@/components/phone/shared/phone-body";
import { PhoneHeader } from "@/components/phone/shared/phone-header";
import { PhoneNotice } from "@/components/phone/shared/phone-notice";

/** The request, or null when it doesn't exist (any other error is thrown). */
async function fetchRequest(requestId: string): Promise<InterventionRequest | null> {
  try {
    return await serverApiFetch<InterventionRequest>(`/api/modules/module-3/intervention-requests/${requestId}`);
  } catch (error) {
    if (error instanceof ServerApiError && (error.status === 404 || error.status === 422)) return null;
    throw error;
  }
}

export default async function RequestPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const [t, tCommon, tErrors, rights] = await Promise.all([
    getTranslations("interventionRequests.phone"),
    getTranslations("common"),
    getTranslations("errors"),
    getInterventionRequestsPhoneRights(),
  ]);
  const canEdit = rights?.canEditRequests ?? false;

  const header = (
    <PhoneHeader
      title={canEdit ? t("changeTitle") : t("viewTitle")}
      backHref={interventionRequestsPhoneRoutes.requests}
      backLabel={tCommon("back")}
      moduleKey="module-3"
    />
  );

  if (!rights?.canViewRequests) {
    return (
      <>
        {header}
        <PhoneBody>
          <PhoneNotice>{tErrors("forbidden")}</PhoneNotice>
        </PhoneBody>
      </>
    );
  }

  const [request, lookups] = await Promise.all([
    fetchRequest(id),
    serverApiFetch<InterventionRequestsLookups>("/api/modules/module-3/lookups"),
  ]);
  if (!request) notFound();

  return (
    <>
      {header}
      <PhoneBody>
        <RequestForm request={request} lookups={lookups} canSave={canEdit} />
      </PhoneBody>
    </>
  );
}
