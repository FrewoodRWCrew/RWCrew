// Walkies's "Users" screen: everyone with access to
// Walkies, their current role, and a "New user" action —
// see UsersManagement for the actual UI. Independently gated from the
// "Roles" screen (../roles/page.tsx) via its own
// "walkies.users" permission.

import { getTranslations } from "next-intl/server";
import { ServerApiError, serverApiFetch } from "@/lib/server-api";
import type { WalkiesRole, WalkiesUserSummary } from "@/lib/types";
import { UsersManagement } from "@/components/module-6/users-management";

export default async function WalkiesUsersPage() {
  const tErrors = await getTranslations("errors");

  let users: WalkiesUserSummary[] | null = null;
  try {
    users = await serverApiFetch<WalkiesUserSummary[]>("/api/modules/module-6/users");
  } catch (error) {
    if (!(error instanceof ServerApiError) || error.status !== 403) {
      throw error;
    }
  }

  if (!users) {
    return <p className="text-sm text-destructive">{tErrors("forbidden")}</p>;
  }

  // The role-assignment dropdown needs role names, but listing roles is
  // gated by the separate "walkies.roles" permission — a
  // user who can manage Users but not Roles simply gets an empty dropdown
  // rather than being locked out of this screen entirely.
  let roles: WalkiesRole[] = [];
  try {
    roles = await serverApiFetch<WalkiesRole[]>("/api/modules/module-6/roles");
  } catch (error) {
    if (!(error instanceof ServerApiError) || error.status !== 403) {
      throw error;
    }
  }

  return <UsersManagement roles={roles} initialUsers={users} />;
}
