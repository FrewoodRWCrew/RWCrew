"use client";

// Tagscan's own left-hand menu, shown while inside the module — visually
// and structurally the same pattern as the landing page's own
// AdminSidebar (a plain "Dashboard" link, then a group heading with
// nested sub-items). Which sub-items actually show depends on the
// current user's Tagscan role: "Roles" and "Users" each only appear if
// they can view that screen ("tagscan.roles" / "tagscan.users",
// independently gated — passed in from the server, which already knows
// how to resolve that — see app/modules/module_1/deps.py).

import { ShieldCheck } from "lucide-react";
import { useTranslations } from "next-intl";
import { Link, usePathname } from "@/i18n/navigation";
import { getModuleTheme } from "@/lib/module-theme";
import { cn } from "@/lib/utils";

interface TagscanSidebarProps {
  viewableScreenKeys: string[];
}

export function TagscanSidebar({ viewableScreenKeys }: TagscanSidebarProps) {
  const t = useTranslations("tagscan");
  // Each link's label reuses that screen's own title, rather than a
  // separate key, so the sidebar and the page heading can never drift apart.
  const tDashboard = useTranslations("tagscan.dashboard");
  const tRoles = useTranslations("tagscan.roles");
  const tUsers = useTranslations("tagscan.users");
  const pathname = usePathname();
  // Reuses the exact same colour as this module's tile on the landing
  // page (see module-theme.ts), so the two can never drift apart.
  const { tileClassName } = getModuleTheme("module-1");

  const canViewRoles = viewableScreenKeys.includes("tagscan.roles");
  const canViewUsers = viewableScreenKeys.includes("tagscan.users");

  function subLinkClassName(href: string) {
    return cn(
      "ml-3 rounded-md px-3 py-2 text-sm font-medium transition-colors",
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

      <Link
        href="/modules/module-1"
        className={cn(
          "rounded-md px-3 py-2 text-sm font-medium transition-colors",
          pathname === "/modules/module-1"
            ? "bg-sidebar-primary text-sidebar-primary-foreground"
            : "text-sidebar-foreground/80 hover:bg-sidebar-accent hover:text-sidebar-accent-foreground",
        )}
      >
        {tDashboard("title")}
      </Link>

      {(canViewRoles || canViewUsers) && (
        <>
          <div className="flex items-center gap-3 px-3 pt-3 pb-1 text-xs font-semibold tracking-wide text-sidebar-foreground/50 uppercase">
            <ShieldCheck className="size-4" />
            {t("accessRights")}
          </div>
          {canViewRoles && (
            <Link href="/modules/module-1/access-rights/roles" className={subLinkClassName("/modules/module-1/access-rights/roles")}>
              {tRoles("title")}
            </Link>
          )}
          {canViewUsers && (
            <Link href="/modules/module-1/access-rights/users" className={subLinkClassName("/modules/module-1/access-rights/users")}>
              {tUsers("title")}
            </Link>
          )}
        </>
      )}
    </nav>
  );
}
