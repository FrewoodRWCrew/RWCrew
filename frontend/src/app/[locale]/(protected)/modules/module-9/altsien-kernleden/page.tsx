// MasterData's "Altsien Kernleden" screen — see AltsienKernledenManagement
// for the actual UI.

import { getTranslations } from "next-intl/server";
import { ServerApiError, serverApiFetch } from "@/lib/server-api";
import type { AltsienKernlid } from "@/lib/types";
import { AltsienKernledenManagement } from "@/components/module-9/altsien-kernleden-management";

export default async function MasterDataAltsienKernledenPage() {
  const tErrors = await getTranslations("errors");

  let contacts: AltsienKernlid[] | null = null;
  try {
    contacts = await serverApiFetch<AltsienKernlid[]>("/api/modules/module-9/altsien-kernleden");
  } catch (error) {
    if (error instanceof ServerApiError && error.status === 403) {
      return <p className="text-sm text-destructive">{tErrors("forbidden")}</p>;
    }
    throw error;
  }

  return <AltsienKernledenManagement initialAltsienKernleden={contacts} />;
}
