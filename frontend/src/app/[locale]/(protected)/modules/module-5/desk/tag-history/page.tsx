// Atelier's "Balie > Tag-historiek" screen — see TagHistory.

import { Suspense } from "react";
import { getTranslations } from "next-intl/server";
import { TagHistory } from "@/components/module-5/tag-history";
import { loadAtelierPage } from "@/components/module-5/atelier-page-data";

export default async function AtelierTagHistoryPage() {
  const data = await loadAtelierPage("taghistory");
  if (!data) {
    const tErrors = await getTranslations("errors");
    return <p className="text-sm text-destructive">{tErrors("forbidden")}</p>;
  }

  // The screen reads ?epc= from the URL (useSearchParams needs a Suspense boundary).
  return (
    <Suspense>
      <TagHistory />
    </Suspense>
  );
}
