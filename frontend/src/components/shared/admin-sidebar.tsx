"use client";

// The left-hand navigation menu, shown only to the super admin. It links
// to the site-wide admin screens (managing user access), plus a link
// back to the tile grid. Modules with their own complete shell (TagScan,
// MasterData) get their own sidebar instead — see MODULES_WITH_OWN_SIDEBAR.

import { LayoutGrid, ShieldCheck } from "lucide-react";
import { useTranslations } from "next-intl";
import { Link, usePathname } from "@/i18n/navigation";
import { cn } from "@/lib/utils";

// Modules that have their own complete left-hand navigation (see
// tagscan-sidebar.tsx / masterdata-sidebar.tsx) — showing this site-wide
// menu alongside one of them would just be a redundant second sidebar.
// The Topbar's logo link already covers "back to the landing page" while
// this is hidden.
const MODULES_WITH_OWN_SIDEBAR = ["/modules/module-1", "/modules/module-9"];

export function AdminSidebar() {
  const t = useTranslations("sidebar");
  const pathname = usePathname();

  if (MODULES_WITH_OWN_SIDEBAR.some((prefix) => pathname.startsWith(prefix))) return null;

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
    </nav>
  );
}
