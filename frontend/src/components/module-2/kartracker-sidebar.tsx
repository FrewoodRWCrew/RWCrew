"use client";

// KarTracker's own left-hand menu, shown while inside the module — same
// visual pattern as TagScan's/Intervention Requests'/MasterData's own
// sidebar (see docs/module-custom-roles-pattern.md): a colored header bar
// matching the module's tile colour, then the unconditional "Dashboard"
// landing link, then grouped sections gated by the current user's
// KarTracker role — see module_2/deps.py.
//
// Groups so far, in display order: "Actions" (the placeholder landing link,
// plus "Kar Planning" — a read-only, cross-table report, and "Kar Map" — a
// read-only map view of Karren/Afleverlocaties/Distributiepunten, each
// gated by its own independent permission), "Masterdata" (KarManagement/
// KarStatussen/Data Upload/Download, the Karlijst phase), and "Access
// Rights" (Roles/Users) — same group order as Intervention Requests' own
// sidebar. Future phases (delivery planning, ...) add their own groups here
// the same way.

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
  const tDistributiepunten = useTranslations("karTracker.distributiepunten");
  const tZones = useTranslations("karTracker.zones");
  const tAfleverlocaties = useTranslations("karTracker.afleverlocaties");
  const tDataUploadDownload = useTranslations("karTracker.dataUploadDownload");
  const tActions = useTranslations("karTracker.actions");
  const tKarPlanning = useTranslations("karTracker.karPlanning");
  const tKarMap = useTranslations("karTracker.karMap");
  const pathname = usePathname();
  // Reuses the exact same colour as this module's tile on the landing
  // page (see module-theme.ts), so the two can never drift apart.
  const { tileClassName } = getModuleTheme("module-2");

  const canViewRoles = viewableScreenKeys.includes("kartracker.roles");
  const canViewUsers = viewableScreenKeys.includes("kartracker.users");
  const canViewKarManagement = viewableScreenKeys.includes("kartracker.karmanagement");
  const canViewKarStatuses = viewableScreenKeys.includes("kartracker.karstatuses");
  const canViewDistributiepunten = viewableScreenKeys.includes("kartracker.distributiepunten");
  const canViewZones = viewableScreenKeys.includes("kartracker.zones");
  const canViewAfleverlocaties = viewableScreenKeys.includes("kartracker.afleverlocaties");
  const canViewDataUploadDownload = viewableScreenKeys.includes("kartracker.dataupload");
  const canViewActions = viewableScreenKeys.includes("kartracker.actions");
  const canViewKarPlanning = viewableScreenKeys.includes("kartracker.karplanning");
  const canViewKarMap = viewableScreenKeys.includes("kartracker.karmap");

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

      {(canViewActions || canViewKarPlanning || canViewKarMap) && (
        <>
          <div className="flex items-center gap-3 px-3 pt-3 pb-1 text-xs font-semibold tracking-wide text-sidebar-foreground/50 uppercase">
            <Zap className="size-4" />
            {t("actionsGroup")}
          </div>
          {canViewActions && (
            <Link href="/modules/module-2/actions" className={linkClassName("/modules/module-2/actions", 1)}>
              {tActions("title")}
            </Link>
          )}
          {canViewKarPlanning && (
            <Link
              href="/modules/module-2/actions/kar-planning"
              className={linkClassName("/modules/module-2/actions/kar-planning", 1)}
            >
              {tKarPlanning("title")}
            </Link>
          )}
          {canViewKarMap && (
            <Link
              href="/modules/module-2/actions/kar-map"
              className={linkClassName("/modules/module-2/actions/kar-map", 1)}
            >
              {tKarMap("title")}
            </Link>
          )}
        </>
      )}

      {(canViewKarManagement ||
        canViewDistributiepunten ||
        canViewZones ||
        canViewAfleverlocaties ||
        canViewKarStatuses ||
        canViewDataUploadDownload) && (
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
          {canViewDistributiepunten && (
            <Link
              href="/modules/module-2/distributiepunten"
              className={linkClassName("/modules/module-2/distributiepunten", 1)}
            >
              {tDistributiepunten("title")}
            </Link>
          )}
          {canViewZones && (
            <Link href="/modules/module-2/zones" className={linkClassName("/modules/module-2/zones", 1)}>
              {tZones("title")}
            </Link>
          )}
          {canViewAfleverlocaties && (
            <Link
              href="/modules/module-2/afleverlocaties"
              className={linkClassName("/modules/module-2/afleverlocaties", 1)}
            >
              {tAfleverlocaties("title")}
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
          {canViewDataUploadDownload && (
            <Link
              href="/modules/module-2/data-upload-download"
              className={linkClassName("/modules/module-2/data-upload-download", 1)}
            >
              {tDataUploadDownload("title")}
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
