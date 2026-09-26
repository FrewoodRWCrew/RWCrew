// Altsien Select's "Request statuses" MasterData screen: the editable list
// of statuses a special request can have — see RequestStatusManagement.
// Gated by the "altsienselect.statuses" screen permission (reading the list
// itself only needs module access, since the follow-up screen needs it too).

import { getTranslations } from "next-intl/server";
import { serverApiFetch } from "@/lib/server-api";
import type { AltsienSelectMyPermissions, AltsienSelectRequestStatus } from "@/lib/types";
import { RequestStatusManagement } from "@/components/module-8/request-status-management";

export default async function RequestStatusesPage() {
  const permissions = await serverApiFetch<AltsienSelectMyPermissions>("/api/modules/module-8/me/permissions");
  if (!permissions.viewable_screen_keys.includes("altsienselect.statuses")) {
    const tErrors = await getTranslations("errors");
    return <p className="text-sm text-destructive">{tErrors("forbidden")}</p>;
  }

  const statuses = await serverApiFetch<AltsienSelectRequestStatus[]>("/api/modules/module-8/request-statuses");

  return <RequestStatusManagement initialStatuses={statuses} />;
}
