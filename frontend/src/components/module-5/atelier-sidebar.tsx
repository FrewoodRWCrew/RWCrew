"use client";

// Atelier's own left-hand menu, shown while inside the module — the
// same visual pattern as Atelier's and StockMaster's sidebars
// (see docs/module-custom-roles-pattern.md): a header bar in the module's
// tile colour, the unconditional "KPI overview" landing link, then "Balie"
// (Uitgifte & inname, Openstaand), "Reservaties" (Reservaties, Voorbereiden), "Stock" (overview, Ontvangst,
// Wassen, Afboeken, Telling, Boekingen, Te bestellen), "Masterdata" (Artikelen with
// Maten nested under it, Data Upload/Download), "Instellingen" (settings,
// Test-scan) and "Access
// Rights" (Roles/Users) — each link gated by the user's Atelier role. The
// next blocks' screens get their own groups above Masterdata.

import { Boxes, CalendarCheck, Database, HandHelping, Settings, ShieldCheck } from "lucide-react";
import { useTranslations } from "next-intl";
import { Link, usePathname } from "@/i18n/navigation";
import { getModuleTheme } from "@/lib/module-theme";
import { cn } from "@/lib/utils";
import { ModuleHelpMenuLink } from "@/components/shared/module-help";

const BASE = "/modules/module-5";

/** One menu link; level 2 = indented under the link above it. */
interface MenuLink {
  href: string;
  label: string;
  level: 1 | 2;
}

interface AtelierSidebarProps {
  viewableScreenKeys: string[];
}

export function AtelierSidebar({ viewableScreenKeys }: AtelierSidebarProps) {
  const t = useTranslations("atelier");
  const pathname = usePathname();
  // Same colour as this module's tile on the landing page.
  const { tileClassName } = getModuleTheme("module-5");

  const can = (screen: string) => viewableScreenKeys.includes(`atelier.${screen}`);
  const canViewRoles = can("roles");
  const canViewUsers = can("users");
  const ARTICLES = `${BASE}/masterdata/articles`;
  const DESK = `${BASE}/desk`;
  const deskLinks: MenuLink[] = [
    ...(can("desk") ? [{ href: DESK, label: t("desk.title"), level: 1 as const }] : []),
    ...(can("open") ? [{ href: `${DESK}/open`, label: t("open.title"), level: 1 as const }] : []),
  ];
  const RESERVATIONS = `${BASE}/reservations`;
  const reservationLinks: MenuLink[] = [
    ...(can("reservations") ? [{ href: RESERVATIONS, label: t("reservations.title"), level: 1 as const }] : []),
    ...(can("preparation")
      ? [{ href: `${RESERVATIONS}/preparation`, label: t("preparation.title"), level: 1 as const }]
      : []),
  ];
  const STOCK = `${BASE}/stock`;
  const stockLinks: MenuLink[] = [
    ...(can("stock") ? [{ href: STOCK, label: t("stock.overview.title"), level: 1 as const }] : []),
    ...(can("receipt") ? [{ href: `${STOCK}/receipt`, label: t("stock.receipt.title"), level: 1 as const }] : []),
    ...(can("wash") ? [{ href: `${STOCK}/wash`, label: t("stock.wash.title"), level: 1 as const }] : []),
    ...(can("writeoff") ? [{ href: `${STOCK}/write-off`, label: t("stock.writeoff.title"), level: 1 as const }] : []),
    ...(can("count") ? [{ href: `${STOCK}/count`, label: t("stock.count.title"), level: 1 as const }] : []),
    ...(can("bookings") ? [{ href: `${STOCK}/bookings`, label: t("stock.bookings.title"), level: 1 as const }] : []),
    ...(can("orderneeds")
      ? [{ href: `${STOCK}/order-needs`, label: t("stock.orderNeeds.title"), level: 1 as const }]
      : []),
  ];
  const SETTINGS = `${BASE}/settings`;
  const settingsLinks: MenuLink[] = [
    ...(can("settings") ? [{ href: SETTINGS, label: t("settings.title"), level: 1 as const }] : []),
    ...(can("scantest") ? [{ href: `${SETTINGS}/scan-test`, label: t("scanTest.title"), level: 1 as const }] : []),
  ];
  // The Masterdata links this user may open (level 2 = nested under Artikelen).
  const masterdataLinks: MenuLink[] = [
    ...(can("articles") ? [{ href: ARTICLES, label: t("articles.title"), level: 1 as const }] : []),
    ...(can("sizes") ? [{ href: `${ARTICLES}/sizes`, label: t("sizes.title"), level: 2 as const }] : []),
    ...(can("dataupload")
      ? [{ href: `${BASE}/masterdata/data-upload-download`, label: t("dataUploadDownload.title"), level: 1 as const }]
      : []),
  ];

  // A link counts as active on its own page and on its sub-pages — except
  // the landing page, Artikelen and Reservaties, whose sub-pages (Maten,
  // Voorbereiden) have links of their own.
  function linkClassName(href: string, level: 0 | 1 | 2 = 0) {
    const isActive = [BASE, ARTICLES, RESERVATIONS, STOCK, DESK, SETTINGS].includes(href)
      ? pathname === href
      : pathname === href || pathname.startsWith(`${href}/`);
    return cn(
      "rounded-md px-3 py-2 text-sm font-medium transition-colors",
      level === 1 && "ml-3 underline",
      level === 2 && "ml-6",
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

      {[
        { icon: HandHelping, label: t("menu.deskGroup"), links: deskLinks },
        { icon: CalendarCheck, label: t("menu.reservationsGroup"), links: reservationLinks },
        { icon: Boxes, label: t("menu.stockGroup"), links: stockLinks },
        { icon: Database, label: t("menu.masterDataGroup"), links: masterdataLinks },
        { icon: Settings, label: t("menu.settingsGroup"), links: settingsLinks },
      ]
        .filter((group) => group.links.length > 0)
        .map((group) => (
          <div key={group.label} className="flex flex-col gap-1">
            <div className={groupClassName}>
              <group.icon className="size-4" />
              {group.label}
            </div>
            {group.links.map((link) => (
              <Link key={link.href} href={link.href} className={linkClassName(link.href, link.level)}>
                {link.label}
              </Link>
            ))}
          </div>
        ))}

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

      <ModuleHelpMenuLink moduleKey="module-5" />
    </nav>
  );
}
