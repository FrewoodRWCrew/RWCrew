// Atelier's "Masterdata > Retourstatussen" screen — see ReturnStatusManagement.

import { getTranslations } from "next-intl/server";
import { serverApiFetch } from "@/lib/server-api";
import type { AtelierReturnStatus } from "@/lib/types";
import { ReturnStatusManagement } from "@/components/module-5/return-status-management";
import { atelierCan, loadAtelierPage } from "@/components/module-5/atelier-page-data";

export default async function AtelierReturnStatusesPage() {
  const data = await loadAtelierPage("returnstatuses");
  if (!data) {
    const tErrors = await getTranslations("errors");
    return <p className="text-sm text-destructive">{tErrors("forbidden")}</p>;
  }

  const statuses = await serverApiFetch<AtelierReturnStatus[]>("/api/modules/module-5/return-statuses");
  return (
    <ReturnStatusManagement
      initialStatuses={statuses}
      canCreate={atelierCan(data.permissions, "returnstatuses", "create")}
      canEdit={atelierCan(data.permissions, "returnstatuses", "edit")}
      canDelete={atelierCan(data.permissions, "returnstatuses", "delete")}
    />
  );
}
