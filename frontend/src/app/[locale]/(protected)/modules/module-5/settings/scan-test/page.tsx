// Atelier's "Instellingen > Test-scan" screen — see ScanTest. Sending needs
// "create" on atelier.scantest.

import { getTranslations } from "next-intl/server";
import { ScanTest } from "@/components/module-5/scan-test";
import { atelierCan, loadAtelierPage } from "@/components/module-5/atelier-page-data";

export default async function AtelierScanTestPage() {
  const data = await loadAtelierPage("scantest");
  if (!data) {
    const tErrors = await getTranslations("errors");
    return <p className="text-sm text-destructive">{tErrors("forbidden")}</p>;
  }

  return <ScanTest canSend={atelierCan(data.permissions, "scantest", "create")} />;
}
