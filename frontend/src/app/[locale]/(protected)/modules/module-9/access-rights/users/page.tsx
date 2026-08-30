// MasterData's "Users" screen: everyone with access to MasterData, their
// current role, and a "New user" action — see UsersManagement for the
// actual UI. Independently gated from the "Roles" screen
// (../roles/page.tsx) via its own "masterdata.users" permission.

import { getTranslations } from "next-intl/server";
import { ServerApiError, serverApiFetch } from "@/lib/server-api";
import type { MasterDataRole, MasterDataUserSummary } from "@/lib/types";
import { UsersManagement } from "@/components/module-9/users-management";

export default async function MasterDataUsersPage() {
  const tErrors = await getTranslations("errors");

  let users: MasterDataUserSummary[] | null = null;
  try {
    users = await serverApiFetch<MasterDataUserSummary[]>("/api/modules/module-9/users");
  } catch (error) {
    if (!(error instanceof ServerApiError) || error.status !== 403) {
      throw error;
    }
  }

  if (!users) {
    return <p className="text-sm text-destructive">{tErrors("forbidden")}</p>;
  }

  // The role-assignment dropdown needs role names, but listing roles is
  // gated by the separate "masterdata.roles" permission — a user who can
  // manage Users but not Roles simply gets an empty dropdown rather than
  // being locked out of this screen entirely.
  let roles: MasterDataRole[] = [];
  try {
    roles = await serverApiFetch<MasterDataRole[]>("/api/modules/module-9/roles");
  } catch (error) {
    if (!(error instanceof ServerApiError) || error.status !== 403) {
      throw error;
    }
  }

  return <UsersManagement roles={roles} initialUsers={users} />;
}
