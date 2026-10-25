// Atelier's "Masterdata > Data Upload/Download" screen — see
// AtelierDataUploadDownload. "View" opens it (templates, exports); the
// upload itself needs "create" on atelier.dataupload.

import { getTranslations } from "next-intl/server";
import { AtelierDataUploadDownload } from "@/components/module-5/atelier-data-upload-download";
import { atelierCan, loadAtelierPage } from "@/components/module-5/atelier-page-data";

export default async function AtelierDataUploadDownloadPage() {
  const data = await loadAtelierPage("dataupload");
  if (!data) {
    const tErrors = await getTranslations("errors");
    return <p className="text-sm text-destructive">{tErrors("forbidden")}</p>;
  }

  return <AtelierDataUploadDownload canUpload={atelierCan(data.permissions, "dataupload", "create")} />;
}
