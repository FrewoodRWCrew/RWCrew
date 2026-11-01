// The super admin's "Wijzigingen" page. Fetches the whole list on the server
// and hands it to the client component (ChangelogTable) that filters it.
//
// Like the Login History page this double-checks the super-admin flag, because
// anyone could type this URL directly.

import { getTranslations } from "next-intl/server";
import { getCurrentUserOnServer } from "@/lib/server-auth";
import { serverApiFetch, ServerApiError } from "@/lib/server-api";
import type { ChangelogEntry } from "@/lib/types";
import { ChangelogTable } from "@/components/admin/changelog-table";

export default async function ChangelogPageRoute() {
  const user = await getCurrentUserOnServer();

  if (!user?.is_super_admin) {
    const tErrors = await getTranslations("errors");
    return <p className="text-sm text-destructive">{tErrors("forbidden")}</p>;
  }

  // 503 = the shared list on GitHub can't be reached: say so on the screen
  // instead of failing the whole page.
  let entries: ChangelogEntry[] | null = null;
  try {
    entries = await serverApiFetch<ChangelogEntry[]>("/api/admin/changelog");
  } catch (error) {
    if (!(error instanceof ServerApiError) || error.status !== 503) throw error;
  }

  return <ChangelogTable entries={entries} />;
}
