// This layout wraps every Altsien Select page (KPI overview, Ploeg Wizard,
// Ploegfiche, request follow-up, statuses and access rights) with the
// module's own left-hand menu, the same way Intervention Requests' own
// layout.tsx does for module-3 — see
// components/module-8/altsien-select-sidebar.tsx for what shows in it.

import { getTranslations } from "next-intl/server";
import { ServerApiError, serverApiFetch } from "@/lib/server-api";
import { getModuleAccentStyle } from "@/lib/module-theme";
import type { AltsienSelectMyPermissions } from "@/lib/types";
import { AltsienSelectSidebar } from "@/components/module-8/altsien-select-sidebar";

interface AltsienSelectLayoutProps {
  children: React.ReactNode;
}

export default async function AltsienSelectLayout({ children }: AltsienSelectLayoutProps) {
  let permissions: AltsienSelectMyPermissions | null = null;
  let forbidden = false;

  try {
    permissions = await serverApiFetch<AltsienSelectMyPermissions>("/api/modules/module-8/me/permissions");
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
    <div className="-m-6 flex min-h-[calc(100vh-3.5rem)]" style={getModuleAccentStyle("module-8")}>
      <AltsienSelectSidebar viewableScreenKeys={permissions.viewable_screen_keys} />
      <div className="min-w-0 flex-1 p-6">{children}</div>
    </div>
  );
}
