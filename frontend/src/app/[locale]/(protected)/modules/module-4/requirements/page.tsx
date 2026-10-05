// StockMaster's "Benodigdheden": what each kar needs per season — see RequirementsEditor.

import { getTranslations } from "next-intl/server";
import { RequirementsEditor } from "@/components/module-4/requirements-editor";
import { canView, loadStockMasterPage } from "@/components/module-4/stockmaster-page-data";

export default async function Page() {
  const data = await loadStockMasterPage(canView("requirements"));
  if (!data) {
    const tErrors = await getTranslations("errors");
    return <p className="text-sm text-destructive">{tErrors("forbidden")}</p>;
  }

  return <RequirementsEditor seasons={data.seasons} permissions={data.permissions} />;
}
