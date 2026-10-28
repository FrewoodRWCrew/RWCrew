// StockMaster's "Spraaktellingen": the kars counted by voice on the phone — see VoiceCountsList.

import { getTranslations } from "next-intl/server";
import { VoiceCountsList } from "@/components/module-4/voice-counts-list";
import { canView, loadStockMasterPage } from "@/components/module-4/stockmaster-page-data";

export default async function Page() {
  const data = await loadStockMasterPage(canView("voicecount"));
  if (!data) {
    const tErrors = await getTranslations("errors");
    return <p className="text-sm text-destructive">{tErrors("forbidden")}</p>;
  }

  return (
    <VoiceCountsList
      seasons={data.seasons}
      canEdit={data.permissions.editable_screen_keys.includes("stockmaster.voicecount")}
    />
  );
}
