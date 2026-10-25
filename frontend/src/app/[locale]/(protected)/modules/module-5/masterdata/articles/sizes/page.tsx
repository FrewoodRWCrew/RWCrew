// Atelier's "Masterdata > Artikelen > Maten" screen — see SizeManagement.

import { getTranslations } from "next-intl/server";
import { serverApiFetch } from "@/lib/server-api";
import type { AtelierSize } from "@/lib/types";
import { SizeManagement } from "@/components/module-5/size-management";
import { atelierCan, loadAtelierPage } from "@/components/module-5/atelier-page-data";

export default async function AtelierSizesPage() {
  const data = await loadAtelierPage("sizes");
  if (!data) {
    const tErrors = await getTranslations("errors");
    return <p className="text-sm text-destructive">{tErrors("forbidden")}</p>;
  }

  const sizes = await serverApiFetch<AtelierSize[]>("/api/modules/module-5/sizes");
  return (
    <SizeManagement
      initialSizes={sizes}
      canCreate={atelierCan(data.permissions, "sizes", "create")}
      canEdit={atelierCan(data.permissions, "sizes", "edit")}
      canDelete={atelierCan(data.permissions, "sizes", "delete")}
    />
  );
}
