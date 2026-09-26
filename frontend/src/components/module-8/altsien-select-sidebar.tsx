"use client";

// Altsien Select's own left-hand menu, shown while inside the module — the
// same visual pattern as Intervention Requests' and KarTracker's sidebars
// (see docs/module-custom-roles-pattern.md): a header bar in the module's
// tile colour, the unconditional "KPI overview" landing link, then the
// "Akties" group (Ploeg Wizard, Ploegfiche, and the organisation's request
// follow-up), the "MasterData" group (request statuses) and "Access Rights"
// (Roles/Users) — each link gated by the user's Altsien Select role.

import { Database, ShieldCheck, Zap } from "lucide-react";
import { useTranslations } from "next-intl";
import { Link, usePathname } from "@/i18n/navigation";
import { getModuleTheme } from "@/lib/module-theme";
import { cn } from "@/lib/utils";

const BASE = "/modules/module-8";

interface AltsienSelectSidebarProps {
  viewableScreenKeys: string[];
}

export function AltsienSelectSidebar({ viewableScreenKeys }: AltsienSelectSidebarProps) {
  const t = useTranslations("altsienSelect");
  const pathname = usePathname();
  // Same colour as this module's tile on the landing page.
  const { tileClassName } = getModuleTheme("module-8");

  const can = (screen: string) => viewableScreenKeys.includes(`altsienselect.${screen}`);
  const canViewWizard = can("wizard");
  const canViewPloegfiche = can("ploegfiche");
  const canViewRequests = can("requests");
  const canViewStatuses = can("statuses");
  const canViewRoles = can("roles");
  const canViewUsers = can("users");

  // A link counts as active on its own page and on its sub-pages (e.g. the
  // wizard of one team under /ploeg-wizard/12).
  function linkClassName(href: string, level: 0 | 1 = 0) {
    const isActive = href === BASE ? pathname === href : pathname === href || pathname.startsWith(`${href}/`);
    return cn(
      "rounded-md px-3 py-2 text-sm font-medium transition-colors",
      level === 1 && "ml-3 underline",
      isActive
        ? "bg-sidebar-primary text-sidebar-primary-foreground"
        : "text-sidebar-foreground/80 hover:bg-sidebar-accent hover:text-sidebar-accent-foreground",
    );
  }

  const groupClassName =
    "flex items-center gap-3 px-3 pt-3 pb-1 text-xs font-semibold tracking-wide text-sidebar-foreground/50 uppercase";

  return (
    <nav className="flex h-full w-60 shrink-0 flex-col gap-1 border-r bg-sidebar p-4 text-sidebar-foreground">
      <div className={cn("-mx-4 -mt-4 mb-2 px-4 py-3 text-sm font-semibold", tileClassName)}>{t("moduleTitle")}</div>

      <Link href={BASE} className={linkClassName(BASE)}>
        {t("landing.title")}
      </Link>

      {(canViewWizard || canViewPloegfiche || canViewRequests) && (
        <>
          <div className={groupClassName}>
            <Zap className="size-4" />
            {t("actionsGroup")}
          </div>
          {canViewWizard && (
            <Link href={`${BASE}/ploeg-wizard`} className={linkClassName(`${BASE}/ploeg-wizard`, 1)}>
              {t("wizard.title")}
            </Link>
          )}
          {canViewPloegfiche && (
            <Link href={`${BASE}/ploegfiche`} className={linkClassName(`${BASE}/ploegfiche`, 1)}>
              {t("ploegfiche.title")}
            </Link>
          )}
          {canViewRequests && (
            <Link href={`${BASE}/requests`} className={linkClassName(`${BASE}/requests`, 1)}>
              {t("followUp.title")}
            </Link>
          )}
        </>
      )}

      {canViewStatuses && (
        <>
          <div className={groupClassName}>
            <Database className="size-4" />
            {t("masterDataGroup")}
          </div>
          <Link href={`${BASE}/request-statuses`} className={linkClassName(`${BASE}/request-statuses`, 1)}>
            {t("status.title")}
          </Link>
        </>
      )}

      {(canViewRoles || canViewUsers) && (
        <>
          <div className={groupClassName}>
            <ShieldCheck className="size-4" />
            {t("accessRights")}
          </div>
          {canViewRoles && (
            <Link href={`${BASE}/access-rights/roles`} className={linkClassName(`${BASE}/access-rights/roles`, 1)}>
              {t("roles.title")}
            </Link>
          )}
          {canViewUsers && (
            <Link href={`${BASE}/access-rights/users`} className={linkClassName(`${BASE}/access-rights/users`, 1)}>
              {t("users.title")}
            </Link>
          )}
        </>
      )}
    </nav>
  );
}
