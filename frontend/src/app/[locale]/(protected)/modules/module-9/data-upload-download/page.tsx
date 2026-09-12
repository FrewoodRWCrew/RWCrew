// MasterData's "Data Upload/Download" screen: a tile grid, one tile per
// master-data table's bulk import/export tools — see
// MasterDataDataUploadDownload for the actual UI. Gated by its own
// screen key ("masterdata.dataupload"), checked here the same way every
// other MasterData screen checks its own permission before rendering
// anything (direct copy of module-2's own data-upload-download/page.tsx).

import { getTranslations } from "next-intl/server";
import { serverApiFetch } from "@/lib/server-api";
import type { MasterDataMyPermissions } from "@/lib/types";
import { MasterDataDataUploadDownload } from "@/components/module-9/masterdata-data-upload-download";

export default async function DataUploadDownloadPage() {
  const tErrors = await getTranslations("errors");

  // Already fetched by this module's layout.tsx for the sidebar — Next.js
  // request memoization means this doesn't trigger a second network call.
  const permissions = await serverApiFetch<MasterDataMyPermissions>("/api/modules/module-9/me/permissions");
  if (!permissions.viewable_screen_keys.includes("masterdata.dataupload")) {
    return <p className="text-sm text-destructive">{tErrors("forbidden")}</p>;
  }

  // "View" is enough to reach this screen and use its template-download/
  // export links, but the upload control itself needs "create" — a
  // view-only user shouldn't be shown a button that will just 403.
  const canUpload = permissions.creatable_screen_keys.includes("masterdata.dataupload");

  return <MasterDataDataUploadDownload canUpload={canUpload} />;
}
