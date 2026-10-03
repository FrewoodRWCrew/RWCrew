// "Akties": the intervention requests as cards, grouped per preferred
// delivery day. Without the right to see requests, only the KPI tab exists.

import { getLocale } from "next-intl/server";
import { redirect } from "@/i18n/navigation";
import { serverApiFetch } from "@/lib/server-api";
import type { InterventionRequest, InterventionRequestsLookups } from "@/lib/types";
import { getInterventionRequestsPhoneRights } from "@/components/phone/module-3/intervention-requests-phone-rights";
import { interventionRequestsPhoneRoutes } from "@/components/phone/module-3/intervention-requests-phone-routes";
import { RequestsList } from "@/components/phone/module-3/requests-list";

export default async function InterventionRequestsActionsPage() {
  const [rights, locale] = await Promise.all([getInterventionRequestsPhoneRights(), getLocale()]);

  if (!rights?.canViewRequests) {
    redirect({ href: interventionRequestsPhoneRoutes.kpi, locale });
  }

  const [requests, lookups] = await Promise.all([
    serverApiFetch<InterventionRequest[]>("/api/modules/module-3/intervention-requests"),
    serverApiFetch<InterventionRequestsLookups>("/api/modules/module-3/lookups"),
  ]);

  return (
    <RequestsList
      requests={requests}
      statuses={lookups.statuses}
      teams={lookups.teams}
      canCreate={rights?.canCreateRequests ?? false}
    />
  );
}
