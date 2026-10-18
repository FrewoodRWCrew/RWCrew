// Atelier's "Users" screen: everyone with access to
// Atelier, their current role, and a "New user" action —
// see UsersManagement for the actual UI. Independently gated from the
// "Roles" screen (../roles/page.tsx) via its own
// "atelier.users" permission.

import { getTranslations } from "next-intl/server";
import { ServerApiError, serverApiFetch } from "@/lib/server-api";
import type { AtelierRole, AtelierUserSummary } from "@/lib/types";
import { UsersManagement } from "@/components/module-5/users-management";

export default async function AtelierUsersPage() {
  const tErrors = await getTranslations("errors");

  let users: AtelierUserSummary[] | null = null;
  try {
    users = await serverApiFetch<AtelierUserSummary[]>("/api/modules/module-5/users");
  } catch (error) {
    if (!(error instanceof ServerApiError) || error.status !== 403) {
      throw error;
    }
  }

  if (!users) {
    return <p className="text-sm text-destructive">{tErrors("forbidden")}</p>;
  }

  // The role-assignment dropdown needs role names, but listing roles is
  // gated by the separate "atelier.roles" permission — a
  // user who can manage Users but not Roles simply gets an empty dropdown
  // rather than being locked out of this screen entirely.
  let roles: AtelierRole[] = [];
  try {
    roles = await serverApiFetch<AtelierRole[]>("/api/modules/module-5/roles");
  } catch (error) {
    if (!(error instanceof ServerApiError) || error.status !== 403) {
      throw error;
    }
  }

  return <UsersManagement roles={roles} initialUsers={users} />;
}
