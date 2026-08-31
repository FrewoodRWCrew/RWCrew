"use client";

// MasterData's own left-hand menu, shown while inside the module —
// direct mirror of TagScan's tagscan-sidebar.tsx (see
// docs/module-custom-roles-pattern.md), with one deliberate difference:
// the top-level "Season" link is gated by its own permission
// ("masterdata.season"), unlike TagScan's unconditional "Dashboard" link
// — Season is real gated content here, not an always-visible landing
// placeholder, so it should behave like every other screen link.
//
// Type/Magazijn/Categorie/Limiet are the four "selection criteria" lookup
// lists used by the Products form — shown indented directly under the
// "Products" link, the same indentation treatment used for Roles/Users
// under "Access Rights" below.

import { ShieldCheck } from "lucide-react";
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
  const tSeason = useTranslations("masterdata.season");
  const tProducts = useTranslations("masterdata.products");
  const tProductTypes = useTranslations("masterdata.productTypes");
  const tWarehouses = useTranslations("masterdata.warehouses");
  const tProductCategories = useTranslations("masterdata.productCategories");
  const tProductLimits = useTranslations("masterdata.productLimits");
  const tRoles = useTranslations("masterdata.roles");
  const tUsers = useTranslations("masterdata.users");
  const pathname = usePathname();
  // Reuses the exact same colour as this module's tile on the landing
  // page (see module-theme.ts), so the two can never drift apart.
  const { tileClassName } = getModuleTheme("module-9");

  const canViewSeason = viewableScreenKeys.includes("masterdata.season");
  const canViewProducts = viewableScreenKeys.includes("masterdata.products");
  const canViewProductTypes = viewableScreenKeys.includes("masterdata.product-types");
  const canViewWarehouses = viewableScreenKeys.includes("masterdata.warehouses");
  const canViewProductCategories = viewableScreenKeys.includes("masterdata.product-categories");
  const canViewProductLimits = viewableScreenKeys.includes("masterdata.product-limits");
  const canViewRoles = viewableScreenKeys.includes("masterdata.roles");
  const canViewUsers = viewableScreenKeys.includes("masterdata.users");

  function linkClassName(href: string, indented = false) {
    return cn(
      "rounded-md px-3 py-2 text-sm font-medium transition-colors",
      indented && "ml-3",
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

      {canViewSeason && (
        <Link href="/modules/module-9" className={linkClassName("/modules/module-9")}>
          {tSeason("title")}
        </Link>
      )}

      {canViewProducts && (
        <Link href="/modules/module-9/products" className={linkClassName("/modules/module-9/products")}>
          {tProducts("title")}
        </Link>
      )}

      {canViewProductTypes && (
        <Link
          href="/modules/module-9/products/types"
          className={linkClassName("/modules/module-9/products/types", true)}
        >
          {tProductTypes("title")}
        </Link>
      )}

      {canViewWarehouses && (
        <Link
          href="/modules/module-9/products/warehouses"
          className={linkClassName("/modules/module-9/products/warehouses", true)}
        >
          {tWarehouses("title")}
        </Link>
      )}

      {canViewProductCategories && (
        <Link
          href="/modules/module-9/products/categories"
          className={linkClassName("/modules/module-9/products/categories", true)}
        >
          {tProductCategories("title")}
        </Link>
      )}

      {canViewProductLimits && (
        <Link
          href="/modules/module-9/products/limits"
          className={linkClassName("/modules/module-9/products/limits", true)}
        >
          {tProductLimits("title")}
        </Link>
      )}

      {(canViewRoles || canViewUsers) && (
        <>
          <div className="flex items-center gap-3 px-3 pt-3 pb-1 text-xs font-semibold tracking-wide text-sidebar-foreground/50 uppercase">
            <ShieldCheck className="size-4" />
            {t("accessRights")}
          </div>
          {canViewRoles && (
            <Link href="/modules/module-9/access-rights/roles" className={linkClassName("/modules/module-9/access-rights/roles", true)}>
              {tRoles("title")}
            </Link>
          )}
          {canViewUsers && (
            <Link href="/modules/module-9/access-rights/users" className={linkClassName("/modules/module-9/access-rights/users", true)}>
              {tUsers("title")}
            </Link>
          )}
        </>
      )}
    </nav>
  );
}
