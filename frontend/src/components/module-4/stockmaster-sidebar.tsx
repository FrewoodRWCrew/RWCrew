"use client";

// StockMaster's own left-hand menu, shown while inside the module — the
// same visual pattern as Altsien Select's and MasterData's sidebars (see
// docs/module-custom-roles-pattern.md): a header bar in the module's tile
// colour, the KPI main page, then the groups Voorraad, Akties (in the
// order of the warehouse process), Planning, Historiek, Instellingen and
// Toegangsrechten — each link gated by the user's StockMaster role.

import { ChartColumn, ClipboardList, Package, ScrollText, Settings, ShieldCheck, Zap, type LucideIcon } from "lucide-react";
import { useTranslations } from "next-intl";
import { Link, usePathname } from "@/i18n/navigation";
import { getModuleTheme } from "@/lib/module-theme";
import type { StockMasterMyPermissions } from "@/lib/types";
import { cn } from "@/lib/utils";
import { ACTION_ORDER, ACTION_PATHS, STOCKMASTER_BASE, canBook } from "@/components/module-4/stockmaster-common";

const BASE = STOCKMASTER_BASE;

interface StockMasterSidebarProps {
  permissions: StockMasterMyPermissions;
}

interface MenuLink {
  href: string;
  label: string;
}

export function StockMasterSidebar({ permissions }: StockMasterSidebarProps) {
  const t = useTranslations("stockMaster");
  const pathname = usePathname();
  // Same colour as this module's tile on the landing page.
  const { tileClassName } = getModuleTheme("module-4");

  const can = (screen: string) => permissions.viewable_screen_keys.includes(`stockmaster.${screen}`);

  // A link counts as active on its own page and on its sub-pages (e.g. one
  // kar under /kars/12) — but "Karren" isn't active on the kar actions.
  const actionHrefs = ACTION_ORDER.map((action) => `${BASE}${ACTION_PATHS[action]}`);
  function isActive(href: string) {
    if (href === BASE) return pathname === href;
    if (pathname === href) return true;
    return pathname.startsWith(`${href}/`) && !actionHrefs.includes(pathname);
  }

  function linkClassName(href: string, level: 0 | 1 = 0) {
    return cn(
      "rounded-md px-3 py-2 text-sm font-medium transition-colors",
      level === 1 && "ml-3 underline",
      isActive(href)
        ? "bg-sidebar-primary text-sidebar-primary-foreground"
        : "text-sidebar-foreground/80 hover:bg-sidebar-accent hover:text-sidebar-accent-foreground",
    );
  }

  const groupClassName =
    "flex items-center gap-3 px-3 pt-3 pb-1 text-xs font-semibold tracking-wide text-sidebar-foreground/50 uppercase";

  // The groups, each listing only the links this user may open.
  const groups: { icon: LucideIcon; label: string; links: MenuLink[] }[] = [
    {
      icon: Package,
      label: t("menu.stockGroup"),
      links: [
        ...(can("stock") ? [{ href: `${BASE}/stock`, label: t("stock.title") }] : []),
        ...(can("kars") ? [{ href: `${BASE}/kars`, label: t("kars.title") }] : []),
      ],
    },
    {
      icon: Zap,
      label: t("menu.actionsGroup"),
      links: ACTION_ORDER.filter((action) =>
        action === "count" ? can("count") : canBook(permissions, action),
      ).map((action, index) => ({
        href: `${BASE}${ACTION_PATHS[action]}`,
        label: `${index + 1}. ${t(`actions.${action}.title`)}`,
      })),
    },
    {
      icon: ClipboardList,
      label: t("menu.planningGroup"),
      links: [
        ...(can("requirements") ? [{ href: `${BASE}/requirements`, label: t("requirements.title") }] : []),
        ...(can("orderneeds") ? [{ href: `${BASE}/order-needs`, label: t("orderNeeds.title") }] : []),
      ],
    },
    {
      icon: ScrollText,
      label: t("menu.historyGroup"),
      links: can("bookings") ? [{ href: `${BASE}/bookings`, label: t("bookings.title") }] : [],
    },
    {
      icon: Settings,
      label: t("menu.settingsGroup"),
      links: can("reasons") ? [{ href: `${BASE}/settings/reasons`, label: t("reasons.title") }] : [],
    },
    {
      icon: ShieldCheck,
      label: t("menu.accessGroup"),
      links: [
        ...(can("roles") ? [{ href: `${BASE}/access-rights/roles`, label: t("roles.title") }] : []),
        ...(can("users") ? [{ href: `${BASE}/access-rights/users`, label: t("users.title") }] : []),
      ],
    },
  ];

  return (
    <nav className="flex h-full w-60 shrink-0 flex-col gap-1 border-r bg-sidebar p-4 text-sidebar-foreground">
      <div className={cn("-mx-4 -mt-4 mb-2 px-4 py-3 text-sm font-semibold", tileClassName)}>{t("moduleTitle")}</div>

      {can("kpi") && (
        <Link href={BASE} className={cn(linkClassName(BASE), "flex items-center gap-3")}>
          <ChartColumn className="size-4" />
          {t("kpi.title")}
        </Link>
      )}

      {groups
        .filter((group) => group.links.length > 0)
        .map(({ icon: Icon, label, links }) => (
          <div key={label} className="flex flex-col gap-1">
            <div className={groupClassName}>
              <Icon className="size-4" />
              {label}
            </div>
            {links.map((link) => (
              <Link key={link.href} href={link.href} className={linkClassName(link.href, 1)}>
                {link.label}
              </Link>
            ))}
          </div>
        ))}
    </nav>
  );
}
