// This layout wraps every StockMaster page with the module's own left-hand
// menu (see components/module-4/stockmaster-sidebar.tsx) and the orange
// minimum-stock banner, the same way Altsien Select's own layout.tsx does
// for module-8.

import { getTranslations } from "next-intl/server";
import { ServerApiError, serverApiFetch } from "@/lib/server-api";
import { getModuleAccentStyle } from "@/lib/module-theme";
import type { StockMasterMyPermissions } from "@/lib/types";
import { MinimumStockBanner } from "@/components/module-4/minimum-stock-banner";
import { StockMasterSidebar } from "@/components/module-4/stockmaster-sidebar";

interface StockMasterLayoutProps {
  children: React.ReactNode;
}

export default async function StockMasterLayout({ children }: StockMasterLayoutProps) {
  let permissions: StockMasterMyPermissions | null = null;
  let forbidden = false;

  try {
    permissions = await serverApiFetch<StockMasterMyPermissions>("/api/modules/module-4/me/permissions");
  } catch (error) {
    if (error instanceof ServerApiError && error.status === 403) {
      forbidden = true;
    } else {
      throw error;
    }
  }

  if (forbidden || !permissions) {
    const tErrors = await getTranslations("errors");
    return <p className="text-sm text-destructive">{tErrors("forbidden")}</p>;
  }

  return (
    // The inline style retints "primary"-coloured UI (active sidebar item,
    // default-variant buttons) to this module's own teal accent.
    <div className="-m-6 flex min-h-[calc(100vh-3.5rem)]" style={getModuleAccentStyle("module-4")}>
      <StockMasterSidebar permissions={permissions} />
      <div className="min-w-0 flex-1 p-6">
        <MinimumStockBanner canOpen={permissions.viewable_screen_keys.includes("stockmaster.stock")} />
        {children}
      </div>
    </div>
  );
}
