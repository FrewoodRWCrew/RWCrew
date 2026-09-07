// Intervention Requests' "Intervention Statuses" screen: the manageable
// lookup list behind the main screen's status dropdown — see
// InterventionStatusManagement for the actual UI.

import { getTranslations } from "next-intl/server";
import { ServerApiError, serverApiFetch } from "@/lib/server-api";
import type { InterventionStatus } from "@/lib/types";
import { InterventionStatusManagement } from "@/components/module-3/intervention-status-management";

export default async function InterventionStatusesPage() {
  const tErrors = await getTranslations("errors");

  let statuses: InterventionStatus[] | null = null;
  try {
    statuses = await serverApiFetch<InterventionStatus[]>("/api/modules/module-3/intervention-statuses");
  } catch (error) {
    if (error instanceof ServerApiError && error.status === 403) {
      return <p className="text-sm text-destructive">{tErrors("forbidden")}</p>;
    }
    throw error;
  }

  return <InterventionStatusManagement initialStatuses={statuses} />;
}
