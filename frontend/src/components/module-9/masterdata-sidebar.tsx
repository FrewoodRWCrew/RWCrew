"use client";

// MasterData's own left-hand menu, shown while inside the module —
// direct mirror of TagScan's tagscan-sidebar.tsx (see
// docs/module-custom-roles-pattern.md). "Overview" (the KPI dashboard,
// now the module's own landing page) is unconditional and stays
// top-level, exactly like TagScan's own "Dashboard" link — always-visible
// landing content, not a gated screen.
//
// "Season", "Festival", "Teams", "Altsien Kernleden", and "Products" ARE
// gated by their own permissions and are grouped under their own
// "MasterData" heading (icon matches this module's own Database icon
// from module-theme.ts), the same visual treatment "Access Rights" gets
// for Roles/Users below. Type/Magazijn/Categorie/Limiet are the four
// "selection criteria" lookup lists used by the Products form — shown
// one level deeper, indented under "Products" within that same group.
// "Teams" itself is currently a placeholder page (see its page.tsx)
// while its own real screen is designed, but Team Location/Delivery
// Method/Team Tasks ARE real, working screens nested one level under it,
// the same way Type/Magazijn/Categorie/Limiet nest under Products.

import { Database, ShieldCheck } from "lucide-react";
import { useTranslations } from "next-intl";
import { Link, usePathname } from "@/i18n/navigation";
import { getModuleTheme } from "@/lib/module-theme";
import { cn } from "@/lib/utils";

interface MasterDataSidebarProps {
  viewableScreenKeys: string[];
}

export function MasterDataSidebar({ viewableScreenKeys }: MasterDataSidebarProps) {
  const t = useTranslations("masterdata");
  // Each link's label reuses that screen's own title, rather than a
  // separate key, so the sidebar and the page heading can never drift apart.
  const tLanding = useTranslations("masterdata.landing");
  const tSeason = useTranslations("masterdata.season");
  const tFestival = useTranslations("masterdata.festival");
  const tTeams = useTranslations("masterdata.teams");
  const tTeamLocation = useTranslations("masterdata.teamLocation");
  const tDeliveryMethod = useTranslations("masterdata.deliveryMethod");
  const tTeamTasks = useTranslations("masterdata.teamTasks");
  const tAltsienKernleden = useTranslations("masterdata.altsienKernleden");
  const tProducts = useTranslations("masterdata.products");
  const tProductTypes = useTranslations("masterdata.productTypes");
  const tWarehouses = useTranslations("masterdata.warehouses");
  const tProductCategories = useTranslations("masterdata.productCategories");
  const tProductLimits = useTranslations("masterdata.productLimits");
  const tRoles = useTranslations("masterdata.roles");
  const tUsers = useTranslations("masterdata.users");
  const tDataUploadDownload = useTranslations("masterdata.dataUploadDownload");
  const pathname = usePathname();
  // Reuses the exact same colour as this module's tile on the landing
  // page (see module-theme.ts), so the two can never drift apart.
  const { tileClassName } = getModuleTheme("module-9");

  const canViewSeason = viewableScreenKeys.includes("masterdata.season");
  const canViewFestival = viewableScreenKeys.includes("masterdata.festival");
  const canViewTeams = viewableScreenKeys.includes("masterdata.teams");
  const canViewTeamLocation = viewableScreenKeys.includes("masterdata.team-location");
  const canViewDeliveryMethod = viewableScreenKeys.includes("masterdata.delivery-method");
  const canViewTeamTasks = viewableScreenKeys.includes("masterdata.team-tasks");
  const canViewAltsienKernleden = viewableScreenKeys.includes("masterdata.altsien-kernleden");
  const canViewProducts = viewableScreenKeys.includes("masterdata.products");
  const canViewProductTypes = viewableScreenKeys.includes("masterdata.product-types");
  const canViewWarehouses = viewableScreenKeys.includes("masterdata.warehouses");
  const canViewProductCategories = viewableScreenKeys.includes("masterdata.product-categories");
  const canViewProductLimits = viewableScreenKeys.includes("masterdata.product-limits");
  const canViewRoles = viewableScreenKeys.includes("masterdata.roles");
  const canViewUsers = viewableScreenKeys.includes("masterdata.users");
  const canViewDataUpload = viewableScreenKeys.includes("masterdata.dataupload");

  function linkClassName(href: string, level: 0 | 1 | 2 = 0) {
    return cn(
      "rounded-md px-3 py-2 text-sm font-medium transition-colors",
      level === 1 && "ml-3 underline",
      level === 2 && "ml-6",
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

      <Link href="/modules/module-9" className={linkClassName("/modules/module-9")}>
        {tLanding("title")}
      </Link>

      {(canViewSeason ||
        canViewFestival ||
        canViewTeams ||
        canViewAltsienKernleden ||
        canViewProducts ||
        canViewDataUpload) && (
        <>
          <div className="flex items-center gap-3 px-3 pt-3 pb-1 text-xs font-semibold tracking-wide text-sidebar-foreground/50 uppercase">
            <Database className="size-4" />
            {t("moduleTitle")}
          </div>

          {canViewSeason && (
            <Link href="/modules/module-9/season" className={linkClassName("/modules/module-9/season", 1)}>
              {tSeason("title")}
            </Link>
          )}

          {canViewFestival && (
            <Link href="/modules/module-9/festival" className={linkClassName("/modules/module-9/festival", 1)}>
              {tFestival("title")}
            </Link>
          )}

          {canViewTeams && (
            <Link href="/modules/module-9/teams" className={linkClassName("/modules/module-9/teams", 1)}>
              {tTeams("title")}
            </Link>
          )}

          {canViewTeamLocation && (
            <Link
              href="/modules/module-9/teams/location"
              className={linkClassName("/modules/module-9/teams/location", 2)}
            >
              {tTeamLocation("title")}
            </Link>
          )}

          {canViewDeliveryMethod && (
            <Link
              href="/modules/module-9/teams/delivery-method"
              className={linkClassName("/modules/module-9/teams/delivery-method", 2)}
            >
              {tDeliveryMethod("title")}
            </Link>
          )}

          {canViewTeamTasks && (
            <Link
              href="/modules/module-9/teams/tasks"
              className={linkClassName("/modules/module-9/teams/tasks", 2)}
            >
              {tTeamTasks("title")}
            </Link>
          )}

          {canViewAltsienKernleden && (
            <Link
              href="/modules/module-9/altsien-kernleden"
              className={linkClassName("/modules/module-9/altsien-kernleden", 1)}
            >
              {tAltsienKernleden("title")}
            </Link>
          )}

          {canViewProducts && (
            <Link href="/modules/module-9/products" className={linkClassName("/modules/module-9/products", 1)}>
              {tProducts("title")}
            </Link>
          )}

          {canViewProductTypes && (
            <Link
              href="/modules/module-9/products/types"
              className={linkClassName("/modules/module-9/products/types", 2)}
            >
              {tProductTypes("title")}
            </Link>
          )}

          {canViewWarehouses && (
            <Link
              href="/modules/module-9/products/warehouses"
              className={linkClassName("/modules/module-9/products/warehouses", 2)}
            >
              {tWarehouses("title")}
            </Link>
          )}

          {canViewProductCategories && (
            <Link
              href="/modules/module-9/products/categories"
              className={linkClassName("/modules/module-9/products/categories", 2)}
            >
              {tProductCategories("title")}
            </Link>
          )}

          {canViewProductLimits && (
            <Link
              href="/modules/module-9/products/limits"
              className={linkClassName("/modules/module-9/products/limits", 2)}
            >
              {tProductLimits("title")}
            </Link>
          )}

          {canViewDataUpload && (
            <Link
              href="/modules/module-9/data-upload-download"
              className={linkClassName("/modules/module-9/data-upload-download", 1)}
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
            <Link href="/modules/module-9/access-rights/roles" className={linkClassName("/modules/module-9/access-rights/roles", 1)}>
              {tRoles("title")}
            </Link>
          )}
          {canViewUsers && (
            <Link href="/modules/module-9/access-rights/users" className={linkClassName("/modules/module-9/access-rights/users", 1)}>
              {tUsers("title")}
            </Link>
          )}
        </>
      )}
    </nav>
  );
}
