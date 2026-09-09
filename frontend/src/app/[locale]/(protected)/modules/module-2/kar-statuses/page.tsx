// KarTracker's "KarStatussen" screen — see KarStatusManagement for the
// actual UI. Permission-checked the normal module way (via this route's
// layout.tsx), plus its own screen-level check here for direct navigation.

import { getTranslations } from "next-intl/server";
import { ServerApiError, serverApiFetch } from "@/lib/server-api";
import type { KarTrackerKarStatus } from "@/lib/types";
import { KarStatusManagement } from "@/components/module-2/kar-status-management";

export default async function KarStatusesPage() {
  const tErrors = await getTranslations("errors");

  let karStatuses: KarTrackerKarStatus[] | null = null;
  try {
    karStatuses = await serverApiFetch<KarTrackerKarStatus[]>("/api/modules/module-2/kar-statuses");
  } catch (error) {
    if (error instanceof ServerApiError && error.status === 403) {
      return <p className="text-sm text-destructive">{tErrors("forbidden")}</p>;
    }
    throw error;
  }

  return <KarStatusManagement initialKarStatuses={karStatuses} />;
}
