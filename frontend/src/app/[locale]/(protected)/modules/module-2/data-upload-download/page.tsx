// KarTracker's "Data Upload/Download" screen: a tile grid, one tile per
// master-data topic's bulk import/export tools. Phase 1 ships a single
// "Karren" tile — see KarDataUploadDownload for the actual UI. Gated by
// its own screen key ("kartracker.dataupload"), checked here the same way
// every other KarTracker screen checks its own permission before
// rendering anything.

import { getTranslations } from "next-intl/server";
import { serverApiFetch } from "@/lib/server-api";
import type { KarTrackerMyPermissions } from "@/lib/types";
import { KarDataUploadDownload } from "@/components/module-2/kar-data-upload-download";

export default async function DataUploadDownloadPage() {
  const tErrors = await getTranslations("errors");

  // Already fetched by this module's layout.tsx for the sidebar — Next.js
  // request memoization means this doesn't trigger a second network call.
  const permissions = await serverApiFetch<KarTrackerMyPermissions>("/api/modules/module-2/me/permissions");
  if (!permissions.viewable_screen_keys.includes("kartracker.dataupload")) {
    return <p className="text-sm text-destructive">{tErrors("forbidden")}</p>;
  }

  return <KarDataUploadDownload />;
}
