"use client";

// KarTracker's own left-hand menu, shown while inside the module — same
// visual pattern as TagScan's/Intervention Requests'/MasterData's own
// sidebar (see docs/module-custom-roles-pattern.md): a colored header bar
// matching the module's tile colour, then the unconditional "Dashboard"
// landing link, then grouped sections gated by the current user's
// KarTracker role — see module_2/deps.py.
//
// Groups so far, in display order: "Actions" (placeholder for now),
// "Masterdata" (KarManagement/KarStatussen, the Karlijst phase), and
// "Access Rights" (Roles/Users) — same group order as Intervention
// Requests' own sidebar. Future phases (delivery planning, ...) add their
// own groups here the same way.

import { Database, ShieldCheck, Zap } from "lucide-react";
import { useTranslations } from "next-intl";
import { Link, usePathname } from "@/i18n/navigation";
import { getModuleTheme } from "@/lib/module-theme";
import { cn } from "@/lib/utils";

interface KarTrackerSidebarProps {
  viewableScreenKeys: string[];
}

export function KarTrackerSidebar({ viewableScreenKeys }: KarTrackerSidebarProps) {
  const t = useTranslations("karTracker");
  const tLanding = useTranslations("karTracker.landing");
  const tRoles = useTranslations("karTracker.roles");
  const tUsers = useTranslations("karTracker.users");
  const tKarManagement = useTranslations("karTracker.karManagement");
  const tKarStatuses = useTranslations("karTracker.karStatuses");
  const tActions = useTranslations("karTracker.actions");
  const pathname = usePathname();
  // Reuses the exact same colour as this module's tile on the landing
  // page (see module-theme.ts), so the two can never drift apart.
  const { tileClassName } = getModuleTheme("module-2");

  const canViewRoles = viewableScreenKeys.includes("kartracker.roles");
  const canViewUsers = viewableScreenKeys.includes("kartracker.users");
  const canViewKarManagement = viewableScreenKeys.includes("kartracker.karmanagement");
  const canViewKarStatuses = viewableScreenKeys.includes("kartracker.karstatuses");
  const canViewActions = viewableScreenKeys.includes("kartracker.actions");

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

      <Link href="/modules/module-2" className={linkClassName("/modules/module-2")}>
        {tLanding("title")}
      </Link>

      {canViewActions && (
        <>
          <div className="flex items-center gap-3 px-3 pt-3 pb-1 text-xs font-semibold tracking-wide text-sidebar-foreground/50 uppercase">
            <Zap className="size-4" />
            {t("actionsGroup")}
          </div>
          <Link href="/modules/module-2/actions" className={linkClassName("/modules/module-2/actions", 1)}>
            {tActions("title")}
          </Link>
        </>
      )}

      {(canViewKarManagement || canViewKarStatuses) && (
        <>
          <div className="flex items-center gap-3 px-3 pt-3 pb-1 text-xs font-semibold tracking-wide text-sidebar-foreground/50 uppercase">
            <Database className="size-4" />
            {t("masterdataGroup")}
          </div>
          {canViewKarManagement && (
            <Link
              href="/modules/module-2/kar-management"
              className={linkClassName("/modules/module-2/kar-management", 1)}
            >
              {tKarManagement("title")}
            </Link>
          )}
          {canViewKarStatuses && (
            <Link
              href="/modules/module-2/kar-statuses"
              className={linkClassName("/modules/module-2/kar-statuses", 1)}
            >
              {tKarStatuses("title")}
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
              href="/modules/module-2/access-rights/roles"
              className={linkClassName("/modules/module-2/access-rights/roles", 1)}
            >
              {tRoles("title")}
            </Link>
          )}
          {canViewUsers && (
            <Link
              href="/modules/module-2/access-rights/users"
              className={linkClassName("/modules/module-2/access-rights/users", 1)}
            >
              {tUsers("title")}
            </Link>
          )}
        </>
      )}
    </nav>
  );
}
