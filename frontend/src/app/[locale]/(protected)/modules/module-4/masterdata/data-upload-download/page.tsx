// StockMaster's "Masterdata > Data Upload/Download" screen: bulk XLSX
// import/export of the products and their four lookup lists — see
// ProductDataUploadDownload. "View" opens it (templates, exports); the
// upload itself needs "create" on stockmaster.dataupload.

import { getTranslations } from "next-intl/server";
import { ProductDataUploadDownload } from "@/components/module-4/product-data-upload-download";
import { canView, loadStockMasterPage } from "@/components/module-4/stockmaster-page-data";

export default async function StockMasterDataUploadDownloadPage() {
  const data = await loadStockMasterPage(canView("dataupload"));
  if (!data) {
    const tErrors = await getTranslations("errors");
    return <p className="text-sm text-destructive">{tErrors("forbidden")}</p>;
  }

  const canUpload = data.permissions.creatable_screen_keys.includes("stockmaster.dataupload");
  return <ProductDataUploadDownload canUpload={canUpload} />;
}
