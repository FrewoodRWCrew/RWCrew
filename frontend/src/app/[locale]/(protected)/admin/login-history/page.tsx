// The super admin's "Login History" page. Fetches the first page of
// login attempts on the server for a fast first paint, then hands it to
// the interactive client component (LoginHistoryTable) that handles
// paging and date-range filtering.
//
// The sidebar link that leads here is only ever shown to the super
// admin, but a non-admin could still type this URL directly — so we
// double-check the flag here too, rather than trusting the sidebar alone.

import { getTranslations } from "next-intl/server";
import { getCurrentUserOnServer } from "@/lib/server-auth";
import { serverApiFetch } from "@/lib/server-api";
import type { LoginHistoryPage } from "@/lib/types";
import { LoginHistoryTable } from "@/components/admin/login-history-table";

const PAGE_SIZE = 50;

export default async function LoginHistoryPageRoute() {
  const user = await getCurrentUserOnServer();

  if (!user?.is_super_admin) {
    const tErrors = await getTranslations("errors");
    return <p className="text-sm text-destructive">{tErrors("forbidden")}</p>;
  }

  const initialData = await serverApiFetch<LoginHistoryPage>(
    `/api/admin/login-history?page=1&page_size=${PAGE_SIZE}`,
  );

  return <LoginHistoryTable initialData={initialData} pageSize={PAGE_SIZE} />;
}
