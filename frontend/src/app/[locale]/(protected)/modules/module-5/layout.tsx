// This layout wraps every Atelier page (KPI overview and access rights)
// with the module's own left-hand menu, the same way Atelier's own
// layout.tsx does for module-5 — see
// components/module-5/atelier-sidebar.tsx for what shows in it.
// Above every page sits the "Help bij dit scherm" link to the manual's
// chapter about the open screen (see components/shared/module-help.tsx), and
// the orange minimum-stock banner when sizes are below their minimum.

import { getTranslations } from "next-intl/server";
import { ServerApiError, serverApiFetch } from "@/lib/server-api";
import { getModuleAccentStyle } from "@/lib/module-theme";
import type { AtelierMyPermissions } from "@/lib/types";
import { AtelierSidebar } from "@/components/module-5/atelier-sidebar";
import { ATELIER_HELP_ROUTES } from "@/components/module-5/atelier-help";
import { ScreenHelpButton } from "@/components/shared/module-help";
import { AtelierMinStockBanner } from "@/components/module-5/atelier-min-stock-banner";

interface AtelierLayoutProps {
  children: React.ReactNode;
}

export default async function AtelierLayout({ children }: AtelierLayoutProps) {
  let permissions: AtelierMyPermissions | null = null;
  let forbidden = false;

  try {
    permissions = await serverApiFetch<AtelierMyPermissions>("/api/modules/module-5/me/permissions");
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
    // The inline style retints "primary"-coloured UI (active sidebar
    // item, default-variant buttons) from the site-wide brand green to
    // this module's own accent colour — see getModuleAccentStyle().
    <div className="-m-6 flex min-h-[calc(100vh-3.5rem)]" style={getModuleAccentStyle("module-5")}>
      <AtelierSidebar viewableScreenKeys={permissions.viewable_screen_keys} />
      <div className="min-w-0 flex-1 p-6">
        <ScreenHelpButton moduleKey="module-5" routes={ATELIER_HELP_ROUTES} className="-mt-4 mb-1" />
        <AtelierMinStockBanner canOpen={permissions.viewable_screen_keys.includes("atelier.stock")} />
        {children}
      </div>
    </div>
  );
}
