// StockMaster on the phone. Like the desktop module layout, it first checks
// that the user may open the module at all; each screen then checks its own
// right (see stockmaster-phone-rights.ts) and draws its own header.

import { getTranslations } from "next-intl/server";
import { getModuleAccentStyle } from "@/lib/module-theme";
import { getStockMasterPhoneRights } from "@/components/phone/module-4/stockmaster-phone-rights";
import { PhoneForbidden } from "@/components/phone/shared/phone-forbidden";

export default async function StockMasterPhoneLayout({ children }: { children: React.ReactNode }) {
  const [t, rights] = await Promise.all([getTranslations("stockMaster"), getStockMasterPhoneRights()]);

  if (rights === null) {
    return <PhoneForbidden title={t("moduleTitle")} />;
  }

  // The module's accent colour becomes the "primary" colour of every button inside.
  return (
    <div className="flex flex-1 flex-col" style={getModuleAccentStyle("module-4")}>
      {children}
    </div>
  );
}
