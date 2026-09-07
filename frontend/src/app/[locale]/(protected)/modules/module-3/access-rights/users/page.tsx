// Intervention Requests' "Users" screen: everyone with access to
// Intervention Requests, their current role, and a "New user" action —
// see UsersManagement for the actual UI. Independently gated from the
// "Roles" screen (../roles/page.tsx) via its own
// "interventionrequests.users" permission.

import { getTranslations } from "next-intl/server";
import { ServerApiError, serverApiFetch } from "@/lib/server-api";
import type { InterventionRequestsRole, InterventionRequestsUserSummary } from "@/lib/types";
import { UsersManagement } from "@/components/module-3/users-management";

export default async function InterventionRequestsUsersPage() {
  const tErrors = await getTranslations("errors");

  let users: InterventionRequestsUserSummary[] | null = null;
  try {
    users = await serverApiFetch<InterventionRequestsUserSummary[]>("/api/modules/module-3/users");
  } catch (error) {
    if (!(error instanceof ServerApiError) || error.status !== 403) {
      throw error;
    }
  }

  if (!users) {
    return <p className="text-sm text-destructive">{tErrors("forbidden")}</p>;
  }

  // The role-assignment dropdown needs role names, but listing roles is
  // gated by the separate "interventionrequests.roles" permission — a
  // user who can manage Users but not Roles simply gets an empty dropdown
  // rather than being locked out of this screen entirely.
  let roles: InterventionRequestsRole[] = [];
  try {
    roles = await serverApiFetch<InterventionRequestsRole[]>("/api/modules/module-3/roles");
  } catch (error) {
    if (!(error instanceof ServerApiError) || error.status !== 403) {
      throw error;
    }
  }

  return <UsersManagement roles={roles} initialUsers={users} />;
}
