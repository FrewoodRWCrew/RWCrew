"use client";

// A tab bar fixed to the bottom of the screen, like a native app's. The tab
// whose page is open is drawn in the module's colour.

import type { LucideIcon } from "lucide-react";
import { Link, usePathname } from "@/i18n/navigation";
import { cn } from "@/lib/utils";

export interface PhoneTab {
  href: string;
  label: string;
  icon: LucideIcon;
}

interface PhoneBottomTabsProps {
  tabs: PhoneTab[];
  /** Tailwind text colour class of the active tab, e.g. "text-orange-600". */
  activeClassName: string;
}

export function PhoneBottomTabs({ tabs, activeClassName }: PhoneBottomTabsProps) {
  const pathname = usePathname();

  return (
    <nav className="sticky bottom-0 z-20 flex border-t bg-background pb-[env(safe-area-inset-bottom)]">
      {tabs.map(({ href, label, icon: Icon }) => {
        const isActive = pathname === href;
        return (
          <Link
            key={href}
            href={href}
            className={cn(
              "flex flex-1 flex-col items-center gap-0.5 py-2 text-xs",
              isActive ? cn("font-semibold", activeClassName) : "text-muted-foreground",
            )}
          >
            <Icon className="size-5" />
            {label}
          </Link>
        );
      })}
    </nav>
  );
}
