// TagScan's "Data Upload/Download" screen: a tile grid with the bulk XLSX
// import/export tools for Tags and Scanners — see TagscanDataUploadDownload
// for the actual UI. Gated by its own screen key ("tagscan.dataupload"),
// the same way MasterData's own data-upload-download/page.tsx does it.

import { getTranslations } from "next-intl/server";
import { serverApiFetch } from "@/lib/server-api";
import type { TagscanMyPermissions } from "@/lib/types";
import { TagscanDataUploadDownload } from "@/components/module-1/tagscan-data-upload-download";

export default async function TagscanDataUploadDownloadPage() {
  const tErrors = await getTranslations("errors");

  // Already fetched by this module's layout.tsx for the sidebar — Next.js
  // request memoization means this doesn't trigger a second network call.
  const permissions = await serverApiFetch<TagscanMyPermissions>("/api/modules/module-1/me/permissions");
  if (!permissions.viewable_screen_keys.includes("tagscan.dataupload")) {
    return <p className="text-sm text-destructive">{tErrors("forbidden")}</p>;
  }

  // "View" is enough for the template/export links; uploading needs "create".
  const canUpload = permissions.creatable_screen_keys.includes("tagscan.dataupload");

  return <TagscanDataUploadDownload canUpload={canUpload} />;
}
