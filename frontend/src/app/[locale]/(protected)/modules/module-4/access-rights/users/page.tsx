// StockMaster's "Users" screen: everyone with access to
// StockMaster, their current role, and a "New user" action —
// see UsersManagement for the actual UI. Independently gated from the
// "Roles" screen (../roles/page.tsx) via its own
// "stockmaster.users" permission.

import { getTranslations } from "next-intl/server";
import { ServerApiError, serverApiFetch } from "@/lib/server-api";
import type { StockMasterRole, StockMasterUserSummary } from "@/lib/types";
import { UsersManagement } from "@/components/module-4/users-management";

export default async function StockMasterUsersPage() {
  const tErrors = await getTranslations("errors");

  let users: StockMasterUserSummary[] | null = null;
  try {
    users = await serverApiFetch<StockMasterUserSummary[]>("/api/modules/module-4/users");
  } catch (error) {
    if (!(error instanceof ServerApiError) || error.status !== 403) {
      throw error;
    }
  }

  if (!users) {
    return <p className="text-sm text-destructive">{tErrors("forbidden")}</p>;
  }

  // The role-assignment dropdown needs role names, but listing roles is
  // gated by the separate "stockmaster.roles" permission — a
  // user who can manage Users but not Roles simply gets an empty dropdown
  // rather than being locked out of this screen entirely.
  let roles: StockMasterRole[] = [];
  try {
    roles = await serverApiFetch<StockMasterRole[]>("/api/modules/module-4/roles");
  } catch (error) {
    if (!(error instanceof ServerApiError) || error.status !== 403) {
      throw error;
    }
  }

  return <UsersManagement roles={roles} initialUsers={users} />;
}
