// One kar in StockMaster: contents versus needs, actions, trip and history
// — see KarDetail.

import { getTranslations } from "next-intl/server";
import { notFound } from "next/navigation";
import { KarDetail } from "@/components/module-4/kar-detail";
import { canView, loadStockMasterPage } from "@/components/module-4/stockmaster-page-data";

interface KarPageProps {
  params: Promise<{ karId: string }>;
}

export default async function KarPage({ params }: KarPageProps) {
  const { karId } = await params;
  const id = Number(karId);
  if (!Number.isInteger(id) || id <= 0) notFound();

  const data = await loadStockMasterPage(canView("kars"));
  if (!data) {
    const tErrors = await getTranslations("errors");
    return <p className="text-sm text-destructive">{tErrors("forbidden")}</p>;
  }

  return <KarDetail karId={id} seasons={data.seasons} permissions={data.permissions} />;
}
