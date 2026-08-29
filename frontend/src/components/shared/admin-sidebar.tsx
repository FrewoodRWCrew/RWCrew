"use client";

// The left-hand navigation menu, shown only to the super admin. It links
// to the admin screens (managing user access, and — later — master
// data), plus a link back to the tile grid.

import { Database, LayoutGrid, ShieldCheck } from "lucide-react";
import { useTranslations } from "next-intl";
import { Link, usePathname } from "@/i18n/navigation";
import { cn } from "@/lib/utils";

// The "Master Data" section is a group of sub-items rather than a single
// link — "Season" is the first one; more can be added here later without
// touching anything else in this file.
const MASTER_DATA_CHILDREN = [{ href: "/admin/master-data/season", labelKey: "masterDataSeason" as const }];

export function AdminSidebar() {
  const t = useTranslations("sidebar");
  const pathname = usePathname();

  // The plain (non-grouped) links this sidebar offers, in order.
  const links = [
    { href: "/", label: t("landing"), icon: LayoutGrid },
    { href: "/admin/access", label: t("manageAccess"), icon: ShieldCheck },
  ];

  return (
    <nav className="flex h-full w-60 shrink-0 flex-col gap-1 border-r bg-sidebar p-4 text-sidebar-foreground">
      {links.map(({ href, label, icon: Icon }) => {
        // Treat the current page as "active" if the URL matches exactly,
        // so the landing link isn't wrongly highlighted while on an
        // admin sub-page.
        const isActive = pathname === href;

        return (
          <Link
            key={href}
            href={href}
            className={cn(
              "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors",
              isActive
                ? "bg-sidebar-primary text-sidebar-primary-foreground"
                : "text-sidebar-foreground/80 hover:bg-sidebar-accent hover:text-sidebar-accent-foreground",
            )}
          >
            <Icon className="size-4" />
            {label}
          </Link>
        );
      })}

      {/* "Master Data" itself is just a group heading — it has no page of
          its own, only the sub-items nested underneath it. */}
      <div className="flex items-center gap-3 px-3 pt-3 pb-1 text-xs font-semibold tracking-wide text-sidebar-foreground/50 uppercase">
        <Database className="size-4" />
        {t("masterData")}
      </div>
      {MASTER_DATA_CHILDREN.map(({ href, labelKey }) => {
        const isActive = pathname === href;

        return (
          <Link
            key={href}
            href={href}
            className={cn(
              "ml-3 rounded-md px-3 py-2 text-sm font-medium transition-colors",
              isActive
                ? "bg-sidebar-primary text-sidebar-primary-foreground"
                : "text-sidebar-foreground/80 hover:bg-sidebar-accent hover:text-sidebar-accent-foreground",
            )}
          >
            {t(labelKey)}
          </Link>
        );
      })}
    </nav>
  );
}
