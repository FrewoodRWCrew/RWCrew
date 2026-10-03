// One row of a module's phone menu: a coloured icon, a bold title with a
// short description under it, and a chevron — the whole row is the link.

import type { LucideIcon } from "lucide-react";
import { ChevronRight } from "lucide-react";
import { Link } from "@/i18n/navigation";
import { getModuleTheme } from "@/lib/module-theme";
import { cn } from "@/lib/utils";

interface PhoneMenuRowProps {
  href: string;
  icon: LucideIcon;
  title: string;
  description: string;
  /** The icon square takes this module's colour. */
  moduleKey: string;
}

export function PhoneMenuRow({ href, icon: Icon, title, description, moduleKey }: PhoneMenuRowProps) {
  return (
    <Link href={href} className="flex items-center gap-3 rounded-xl border bg-card p-3 active:bg-muted">
      <span
        className={cn(
          "flex size-11 shrink-0 items-center justify-center rounded-lg",
          getModuleTheme(moduleKey).tileClassName,
        )}
      >
        <Icon className="size-5" />
      </span>
      <span className="flex min-w-0 flex-1 flex-col">
        <span className="font-semibold">{title}</span>
        <span className="text-sm text-muted-foreground">{description}</span>
      </span>
      <ChevronRight className="size-5 shrink-0 text-muted-foreground" />
    </Link>
  );
}
