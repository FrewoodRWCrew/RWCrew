// The super admin's "Season" master-data screen — reached via the
// "Master Data" > "Season" sub-item in the admin sidebar. "Season" is
// the first master-data entity; more would get their own similar
// sibling route folder here later (e.g. admin/master-data/<entity>/).

import { getTranslations } from "next-intl/server";
import { getCurrentUserOnServer } from "@/lib/server-auth";
import { serverApiFetch } from "@/lib/server-api";
import type { Season } from "@/lib/types";
import { SeasonManagement } from "@/components/admin/season-management";

export default async function SeasonPage() {
  const user = await getCurrentUserOnServer();
  const tErrors = await getTranslations("errors");

  if (!user?.is_super_admin) {
    return <p className="text-sm text-destructive">{tErrors("forbidden")}</p>;
  }

  const t = await getTranslations("admin.masterData");
  const seasons = await serverApiFetch<Season[]>("/api/admin/master-data/seasons");

  return (
    <div className="flex flex-col gap-6">
      <h1 className="text-2xl font-semibold tracking-tight">{t("title")}</h1>
      <SeasonManagement initialSeasons={seasons} />
    </div>
  );
}
