// The Scans module's wristband "Scanners" screen — see WristbandScanners.
// Changing a label needs "edit" on tagscan.wristband-scanners.

import { getTranslations } from "next-intl/server";
import { serverApiFetch } from "@/lib/server-api";
import type { TagscanMyPermissions } from "@/lib/types";
import { WristbandScanners } from "@/components/module-1/wristband-scanners";

export default async function WristbandScannersPage() {
  const permissions = await serverApiFetch<TagscanMyPermissions>("/api/modules/module-1/me/permissions");
  if (!permissions.viewable_screen_keys.includes("tagscan.wristband-scanners")) {
    const tErrors = await getTranslations("errors");
    return <p className="text-sm text-destructive">{tErrors("forbidden")}</p>;
  }
  return <WristbandScanners canEdit={permissions.editable_screen_keys.includes("tagscan.wristband-scanners")} />;
}
