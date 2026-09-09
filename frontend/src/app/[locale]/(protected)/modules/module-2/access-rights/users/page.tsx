// KarTracker's "Users" screen: everyone with access to KarTracker, their
// current role, and a "New user" action — see UsersManagement for the
// actual UI. Independently gated from the "Roles" screen (../roles/page.tsx)
// via its own "kartracker.users" permission.

import { getTranslations } from "next-intl/server";
import { ServerApiError, serverApiFetch } from "@/lib/server-api";
import type { KarTrackerRole, KarTrackerUserSummary } from "@/lib/types";
import { UsersManagement } from "@/components/module-2/users-management";

export default async function KarTrackerUsersPage() {
  const tErrors = await getTranslations("errors");

  let users: KarTrackerUserSummary[] | null = null;
  try {
    users = await serverApiFetch<KarTrackerUserSummary[]>("/api/modules/module-2/users");
  } catch (error) {
    if (!(error instanceof ServerApiError) || error.status !== 403) {
      throw error;
    }
  }

  if (!users) {
    return <p className="text-sm text-destructive">{tErrors("forbidden")}</p>;
  }

  // The role-assignment dropdown needs role names, but listing roles is
  // gated by the separate "kartracker.roles" permission — a user who can
  // manage Users but not Roles simply gets an empty dropdown rather than
  // being locked out of this screen entirely.
  let roles: KarTrackerRole[] = [];
  try {
    roles = await serverApiFetch<KarTrackerRole[]>("/api/modules/module-2/roles");
  } catch (error) {
    if (!(error instanceof ServerApiError) || error.status !== 403) {
      throw error;
    }
  }

  return <UsersManagement roles={roles} initialUsers={users} />;
}
