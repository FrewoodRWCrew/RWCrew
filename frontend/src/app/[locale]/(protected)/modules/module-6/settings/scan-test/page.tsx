// Walkies' "Instellingen > Test-scan" screen — see ScanTest. Walkies has no
// counter yet (phase 2), so the screen says where a scan shows up for now.
// Sending needs "create" on walkies.scantest.

import { getTranslations } from "next-intl/server";
import { serverApiFetch } from "@/lib/server-api";
import type { WalkiesMyPermissions } from "@/lib/types";
import { ScanTest } from "@/components/shared/wristband/scan-test";

export default async function WalkiesScanTestPage() {
  const permissions = await serverApiFetch<WalkiesMyPermissions>("/api/modules/module-6/me/permissions");
  if (!permissions.viewable_screen_keys.includes("walkies.scantest")) {
    const tErrors = await getTranslations("errors");
    return <p className="text-sm text-destructive">{tErrors("forbidden")}</p>;
  }
  const t = await getTranslations("walkies.scanTest");
  return (
    <ScanTest
      moduleKey="module-6"
      canSend={permissions.creatable_screen_keys.includes("walkies.scantest")}
      note={t("note")}
    />
  );
}
