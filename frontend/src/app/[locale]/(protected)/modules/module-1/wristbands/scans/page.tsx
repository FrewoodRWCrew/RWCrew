// The Scans module's wristband "Scans" screen — see WristbandScans. The
// scanner filter only shows with view on the Scanners screen.

import { getTranslations } from "next-intl/server";
import { serverApiFetch } from "@/lib/server-api";
import type { TagscanMyPermissions } from "@/lib/types";
import { WristbandScans } from "@/components/module-1/wristband-scans";

export default async function WristbandScansPage() {
  const permissions = await serverApiFetch<TagscanMyPermissions>("/api/modules/module-1/me/permissions");
  if (!permissions.viewable_screen_keys.includes("tagscan.wristband-scans")) {
    const tErrors = await getTranslations("errors");
    return <p className="text-sm text-destructive">{tErrors("forbidden")}</p>;
  }
  return <WristbandScans canViewScanners={permissions.viewable_screen_keys.includes("tagscan.wristband-scanners")} />;
}
