"use client";

// Intervention Requests' own left-hand menu, shown while inside the
// module — same visual pattern as TagScan's/MasterData's own sidebar
// (see docs/module-custom-roles-pattern.md): a colored header bar
// matching the module's tile colour, then the unconditional "KPI
// overview" landing link, then an "Actions" group (the main Intervention
// Requests screen) and a "MasterData" group (the Intervention Statuses
// lookup screen), and an "Access Rights" group (Roles/Users) — all now
// gated by the current user's Intervention Requests role, the same way
// TagScan's/MasterData's own sidebar are (see module_3/deps.py).

import { Database, ShieldCheck, Zap } from "lucide-react";
import { useTranslations } from "next-intl";
import { Link, usePathname } from "@/i18n/navigation";
import { getModuleTheme } from "@/lib/module-theme";
import { cn } from "@/lib/utils";

interface InterventionRequestsSidebarProps {
  viewableScreenKeys: string[];
}

export function InterventionRequestsSidebar({ viewableScreenKeys }: InterventionRequestsSidebarProps) {
  const t = useTranslations("interventionRequests");
  const tLanding = useTranslations("interventionRequests.landing");
  const tRequests = useTranslations("interventionRequests.requests");
  const tStatus = useTranslations("interventionRequests.status");
  const tTeamKar = useTranslations("interventionRequests.teamkar");
  const tRoles = useTranslations("interventionRequests.roles");
  const tUsers = useTranslations("interventionRequests.users");
  const pathname = usePathname();
  // Reuses the exact same colour as this module's tile on the landing
  // page (see module-theme.ts), so the two can never drift apart.
  const { tileClassName } = getModuleTheme("module-3");

  const canViewRequests = viewableScreenKeys.includes("interventionrequests.requests");
  const canViewStatuses = viewableScreenKeys.includes("interventionrequests.statuses");
  const canViewTeamKar = viewableScreenKeys.includes("interventionrequests.teamkar");
  const canViewRoles = viewableScreenKeys.includes("interventionrequests.roles");
  const canViewUsers = viewableScreenKeys.includes("interventionrequests.users");

  function linkClassName(href: string, level: 0 | 1 = 0) {
    return cn(
      "rounded-md px-3 py-2 text-sm font-medium transition-colors",
      level === 1 && "ml-3 underline",
      pathname === href
        ? "bg-sidebar-primary text-sidebar-primary-foreground"
        : "text-sidebar-foreground/80 hover:bg-sidebar-accent hover:text-sidebar-accent-foreground",
    );
  }

  return (
    <nav className="flex h-full w-60 shrink-0 flex-col gap-1 border-r bg-sidebar p-4 text-sidebar-foreground">
      <div className={cn("-mx-4 -mt-4 mb-2 px-4 py-3 text-sm font-semibold", tileClassName)}>
        {t("moduleTitle")}
      </div>

      <Link href="/modules/module-3" className={linkClassName("/modules/module-3")}>
        {tLanding("title")}
      </Link>

      {canViewRequests && (
        <>
          <div className="flex items-center gap-3 px-3 pt-3 pb-1 text-xs font-semibold tracking-wide text-sidebar-foreground/50 uppercase">
            <Zap className="size-4" />
            {t("actionsGroup")}
          </div>
          <Link
            href="/modules/module-3/intervention-requests"
            className={linkClassName("/modules/module-3/intervention-requests", 1)}
          >
            {tRequests("title")}
          </Link>
        </>
      )}

      {(canViewStatuses || canViewTeamKar) && (
        <>
          <div className="flex items-center gap-3 px-3 pt-3 pb-1 text-xs font-semibold tracking-wide text-sidebar-foreground/50 uppercase">
            <Database className="size-4" />
            {t("masterDataGroup")}
          </div>
          {canViewStatuses && (
            <Link
              href="/modules/module-3/intervention-statuses"
              className={linkClassName("/modules/module-3/intervention-statuses", 1)}
            >
              {tStatus("title")}
            </Link>
          )}
          {canViewTeamKar && (
            <Link href="/modules/module-3/teamkar" className={linkClassName("/modules/module-3/teamkar", 1)}>
              {tTeamKar("title")}
            </Link>
          )}
        </>
      )}

      {(canViewRoles || canViewUsers) && (
        <>
          <div className="flex items-center gap-3 px-3 pt-3 pb-1 text-xs font-semibold tracking-wide text-sidebar-foreground/50 uppercase">
            <ShieldCheck className="size-4" />
            {t("accessRights")}
          </div>
          {canViewRoles && (
            <Link
              href="/modules/module-3/access-rights/roles"
              className={linkClassName("/modules/module-3/access-rights/roles", 1)}
            >
              {tRoles("title")}
            </Link>
          )}
          {canViewUsers && (
            <Link
              href="/modules/module-3/access-rights/users"
              className={linkClassName("/modules/module-3/access-rights/users", 1)}
            >
              {tUsers("title")}
            </Link>
          )}
        </>
      )}
    </nav>
  );
}
