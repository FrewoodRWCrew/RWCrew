// Intervention Requests' "Roles" screen: create/rename/delete custom
// roles and edit each role's permission matrix (view/create/edit/delete
// per screen) — see RolesManagement for the actual UI. User management
// lives on its own separate "Users" screen (../users/page.tsx).

import { getTranslations } from "next-intl/server";
import { ServerApiError, serverApiFetch } from "@/lib/server-api";
import type { InterventionRequestsRole, InterventionRequestsScreen } from "@/lib/types";
import { RolesManagement } from "@/components/module-3/roles-management";

interface RolesPageData {
  screens: InterventionRequestsScreen[];
  roles: InterventionRequestsRole[];
}

export default async function InterventionRequestsRolesPage() {
  const tErrors = await getTranslations("errors");

  let data: RolesPageData | null = null;
  try {
    const [screens, roles] = await Promise.all([
      serverApiFetch<InterventionRequestsScreen[]>("/api/modules/module-3/screens"),
      serverApiFetch<InterventionRequestsRole[]>("/api/modules/module-3/roles"),
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
