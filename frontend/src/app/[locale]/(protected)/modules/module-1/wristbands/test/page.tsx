// The Scans module's "Test scan" screen — see ScanTest. Sending needs
// "create" on tagscan.wristband-test.

import { getTranslations } from "next-intl/server";
import { serverApiFetch } from "@/lib/server-api";
import type { TagscanMyPermissions } from "@/lib/types";
import { ScanTest } from "@/components/shared/wristband/scan-test";

export default async function WristbandTestPage() {
  const permissions = await serverApiFetch<TagscanMyPermissions>("/api/modules/module-1/me/permissions");
  if (!permissions.viewable_screen_keys.includes("tagscan.wristband-test")) {
    const tErrors = await getTranslations("errors");
    return <p className="text-sm text-destructive">{tErrors("forbidden")}</p>;
  }
  return <ScanTest moduleKey="module-1" canSend={permissions.creatable_screen_keys.includes("tagscan.wristband-test")} />;
}
