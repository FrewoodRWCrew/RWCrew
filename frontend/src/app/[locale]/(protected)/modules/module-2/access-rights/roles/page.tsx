// KarTracker's "Roles" screen: create/rename/delete custom roles and edit
// each role's permission matrix (view/create/edit/delete per screen) — see
// RolesManagement for the actual UI. User management lives on its own
// separate "Users" screen (../users/page.tsx).

import { getTranslations } from "next-intl/server";
import { ServerApiError, serverApiFetch } from "@/lib/server-api";
import type { KarTrackerRole, KarTrackerScreen } from "@/lib/types";
import { RolesManagement } from "@/components/module-2/roles-management";

interface RolesPageData {
  screens: KarTrackerScreen[];
  roles: KarTrackerRole[];
}

export default async function KarTrackerRolesPage() {
  const tErrors = await getTranslations("errors");

  let data: RolesPageData | null = null;
  try {
    const [screens, roles] = await Promise.all([
      serverApiFetch<KarTrackerScreen[]>("/api/modules/module-2/screens"),
      serverApiFetch<KarTrackerRole[]>("/api/modules/module-2/roles"),
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
