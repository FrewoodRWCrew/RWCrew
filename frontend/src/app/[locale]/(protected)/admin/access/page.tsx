// The super admin's "Manage Access" page. Fetches the current users and
// modules on the server, then hands them to the interactive client
// component (AccessManagement) that renders the checkbox grid.
//
// The sidebar link that leads here is only ever shown to the super
// admin, but a non-admin could still type this URL directly — so we
// double-check the flag here too, rather than trusting the sidebar alone.

import { getTranslations } from "next-intl/server";
import { getCurrentUserOnServer } from "@/lib/server-auth";
import { serverApiFetch } from "@/lib/server-api";
import type { ModuleInfo, UserSummary } from "@/lib/types";
import { AccessManagement } from "@/components/admin/access-management";

export default async function AccessManagementPage() {
  const user = await getCurrentUserOnServer();

  if (!user?.is_super_admin) {
    const tErrors = await getTranslations("errors");
    return <p className="text-sm text-destructive">{tErrors("forbidden")}</p>;
  }

  const [users, modules] = await Promise.all([
    serverApiFetch<UserSummary[]>("/api/admin/users"),
    serverApiFetch<ModuleInfo[]>("/api/modules"),
  ]);

  return <AccessManagement initialUsers={users} modules={modules} currentUserId={user.id} />;
}
