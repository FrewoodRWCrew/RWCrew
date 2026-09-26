// Altsien Select's "Users" screen: everyone with access to
// Altsien Select, their current role, and a "New user" action —
// see UsersManagement for the actual UI. Independently gated from the
// "Roles" screen (../roles/page.tsx) via its own
// "altsienselect.users" permission.

import { getTranslations } from "next-intl/server";
import { ServerApiError, serverApiFetch } from "@/lib/server-api";
import type { AltsienSelectRole, AltsienSelectUserSummary } from "@/lib/types";
import { UsersManagement } from "@/components/module-8/users-management";

export default async function AltsienSelectUsersPage() {
  const tErrors = await getTranslations("errors");

  let users: AltsienSelectUserSummary[] | null = null;
  try {
    users = await serverApiFetch<AltsienSelectUserSummary[]>("/api/modules/module-8/users");
  } catch (error) {
    if (!(error instanceof ServerApiError) || error.status !== 403) {
      throw error;
    }
  }

  if (!users) {
    return <p className="text-sm text-destructive">{tErrors("forbidden")}</p>;
  }

  // The role-assignment dropdown needs role names, but listing roles is
  // gated by the separate "altsienselect.roles" permission — a
  // user who can manage Users but not Roles simply gets an empty dropdown
  // rather than being locked out of this screen entirely.
  let roles: AltsienSelectRole[] = [];
  try {
    roles = await serverApiFetch<AltsienSelectRole[]>("/api/modules/module-8/roles");
  } catch (error) {
    if (!(error instanceof ServerApiError) || error.status !== 403) {
      throw error;
    }
  }

  return <UsersManagement roles={roles} initialUsers={users} />;
}
