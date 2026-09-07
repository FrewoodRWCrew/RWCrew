// This layout wraps every Intervention Requests page (KPI overview and
// everything under access-rights/) with the module's own left-hand menu,
// the same way TagScan's/MasterData's own layout.tsx do for
// module-1/module-9 — see
// components/module-3/intervention-requests-sidebar.tsx for what shows in
// it and why.

import { getTranslations } from "next-intl/server";
import { ServerApiError, serverApiFetch } from "@/lib/server-api";
import { getModuleAccentStyle } from "@/lib/module-theme";
import type { InterventionRequestsMyPermissions } from "@/lib/types";
import { InterventionRequestsSidebar } from "@/components/module-3/intervention-requests-sidebar";

interface InterventionRequestsLayoutProps {
  children: React.ReactNode;
}

export default async function InterventionRequestsLayout({ children }: InterventionRequestsLayoutProps) {
  let permissions: InterventionRequestsMyPermissions | null = null;
  let forbidden = false;

  try {
    permissions = await serverApiFetch<InterventionRequestsMyPermissions>("/api/modules/module-3/me/permissions");
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
    <div className="-m-6 flex min-h-[calc(100vh-3.5rem)]" style={getModuleAccentStyle("module-3")}>
      <InterventionRequestsSidebar viewableScreenKeys={permissions.viewable_screen_keys} />
      <div className="min-w-0 flex-1 p-6">{children}</div>
    </div>
  );
}
