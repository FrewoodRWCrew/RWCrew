// This layout wraps every MasterData page (Season and everything under
// access-rights/) with MasterData's own left-hand menu, the same way
// TagScan's own layout.tsx does for module-1 — see
// components/module-9/masterdata-sidebar.tsx for what shows in it and why.

import { getTranslations } from "next-intl/server";
import { ServerApiError, serverApiFetch } from "@/lib/server-api";
import { getModuleAccentStyle } from "@/lib/module-theme";
import type { MasterDataMyPermissions } from "@/lib/types";
import { MasterDataSidebar } from "@/components/module-9/masterdata-sidebar";

interface MasterDataLayoutProps {
  children: React.ReactNode;
}

export default async function MasterDataLayout({ children }: MasterDataLayoutProps) {
  let permissions: MasterDataMyPermissions | null = null;
  let forbidden = false;

  try {
    permissions = await serverApiFetch<MasterDataMyPermissions>("/api/modules/module-9/me/permissions");
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
    <div className="-m-6 flex min-h-[calc(100vh-3.5rem)]" style={getModuleAccentStyle("module-9")}>
      <MasterDataSidebar viewableScreenKeys={permissions.viewable_screen_keys} />
      <div className="min-w-0 flex-1 p-6">{children}</div>
    </div>
  );
}
