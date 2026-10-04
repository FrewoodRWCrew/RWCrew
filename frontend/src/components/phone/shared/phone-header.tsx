// The bar at the top of every phone screen: an optional back arrow, the
// screen's title, the light/dark switch, and an optional action on the right
// (e.g. "Uitloggen").
// Inside a module it takes that module's own colour (module-theme.ts), the
// same way the old phone app's headers did.

import type { ReactNode } from "react";
import { ChevronLeft } from "lucide-react";
import { Link } from "@/i18n/navigation";
import { getModuleTheme } from "@/lib/module-theme";
import { cn } from "@/lib/utils";
import { ThemeToggle } from "@/components/shared/theme-toggle";

interface PhoneHeaderProps {
  title: string;
  /** Where the back arrow goes; no arrow when left out (the home page). */
  backHref?: string;
  /** Accessible name of the back arrow. */
  backLabel?: string;
  /** Colours the bar in this module's accent; plain when left out. */
  moduleKey?: string;
  /** Shown at the right end of the bar. */
  action?: ReactNode;
}

export function PhoneHeader({ title, backHref, backLabel, moduleKey, action }: PhoneHeaderProps) {
  const colorClassName = moduleKey ? getModuleTheme(moduleKey).tileClassName : "border-b bg-background";

  return (
    <header className={cn("sticky top-0 z-20 flex h-14 shrink-0 items-center gap-1 px-2", colorClassName)}>
      {backHref ? (
        <Link
          href={backHref}
          aria-label={backLabel}
          className="flex size-10 items-center justify-center rounded-full active:bg-black/10"
        >
          <ChevronLeft className="size-6" />
        </Link>
      ) : (
        <span className="w-2" />
      )}
      <h1 className="min-w-0 flex-1 truncate text-lg font-semibold">{title}</h1>
      {/* Light/dark switch (same as the desktop top bar's); the choice is
          remembered on the phone. Takes the header's own text colour. */}
      <ThemeToggle className="size-10 text-inherit hover:bg-black/10 hover:text-inherit [&_svg]:size-5" />
      {action && <div className="shrink-0 pr-2">{action}</div>}
    </header>
  );
}
