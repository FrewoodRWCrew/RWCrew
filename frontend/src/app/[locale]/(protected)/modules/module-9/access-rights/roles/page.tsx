// MasterData's "Roles" screen: create/rename/delete custom roles and edit
// each role's permission matrix (view/create/edit/delete per screen) —
// see RolesManagement for the actual UI. User management lives on its
// own separate "Users" screen (../users/page.tsx).

import { getTranslations } from "next-intl/server";
import { ServerApiError, serverApiFetch } from "@/lib/server-api";
import type { MasterDataRole, MasterDataScreen } from "@/lib/types";
import { RolesManagement } from "@/components/module-9/roles-management";

interface RolesPageData {
  screens: MasterDataScreen[];
  roles: MasterDataRole[];
}

export default async function MasterDataRolesPage() {
  const tErrors = await getTranslations("errors");

  let data: RolesPageData | null = null;
  try {
    const [screens, roles] = await Promise.all([
      serverApiFetch<MasterDataScreen[]>("/api/modules/module-9/screens"),
      serverApiFetch<MasterDataRole[]>("/api/modules/module-9/roles"),
    ]);
    data = { screens, roles };
  } catch (error) {
    if (!(error instanceof ServerApiError) || error.status !== 403) {
      throw error;
    }
  }

  if (!data) {
    return <p className="text-sm text-destructive">{tErrors("forbidden")}</p>;
  }

  return <RolesManagement initialScreens={data.screens} initialRoles={data.roles} />;
}
