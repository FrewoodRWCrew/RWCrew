// Atelier's "Balie > Retourproblemen" screen — see ReturnIssues.

import { getTranslations } from "next-intl/server";
import { ReturnIssues } from "@/components/module-5/return-issues";
import { loadAtelierPage } from "@/components/module-5/atelier-page-data";

export default async function AtelierReturnIssuesPage() {
  const data = await loadAtelierPage("returnissues");
  if (!data) {
    const tErrors = await getTranslations("errors");
    return <p className="text-sm text-destructive">{tErrors("forbidden")}</p>;
  }

  return <ReturnIssues seasons={data.seasons} />;
}
