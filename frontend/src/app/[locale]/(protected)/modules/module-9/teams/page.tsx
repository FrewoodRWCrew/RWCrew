// MasterData's "Teams" screen — placeholder only, until the real screen
// is designed. Still permission-gated by "masterdata.teams" like every
// other MasterData screen, even though there's no real data yet: this
// page checks its own view permission directly (no Teams API to 403
// against yet, unlike season/page.tsx or festival/page.tsx).

import { getTranslations } from "next-intl/server";
import { serverApiFetch } from "@/lib/server-api";
import type { MasterDataMyPermissions } from "@/lib/types";

export default async function MasterDataTeamsPage() {
  const t = await getTranslations("masterdata.teams");
  const tErrors = await getTranslations("errors");

  const permissions = await serverApiFetch<MasterDataMyPermissions>("/api/modules/module-9/me/permissions");
  if (!permissions.viewable_screen_keys.includes("masterdata.teams")) {
    return <p className="text-sm text-destructive">{tErrors("forbidden")}</p>;
  }

  return (
    <div className="flex flex-col gap-4">
      <h1 className="text-2xl font-bold tracking-tight underline">{t("title")}</h1>
      <p className="text-muted-foreground">{t("comingSoon")}</p>
    </div>
  );
}
