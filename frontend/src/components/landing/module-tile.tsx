// One tile on the landing page, representing a single module. The
// landing page only ever passes in modules the current user has access
// to (see page.tsx), so every tile rendered here is always a clickable
// link — no locked/greyed-out state to handle. The whole tile is filled
// with the module's own accent colour (see module-theme.ts), not just a
// small badge, so each module reads clearly at a glance.

import { Link } from "@/i18n/navigation";
import { cn } from "@/lib/utils";
import { getModuleNumber, getModuleTheme } from "@/lib/module-theme";
import type { ModuleInfo } from "@/lib/types";

interface ModuleTileProps {
  module: ModuleInfo;
}

export function ModuleTile({ module }: ModuleTileProps) {
  const theme = getModuleTheme(module.key);
  const number = getModuleNumber(module.key);
  const Icon = theme.icon;

  return (
    <Link href={`/modules/${module.key}`} className="block">
      <div
        className={cn(
          "relative flex h-36 flex-col rounded-xl p-4 shadow-sm transition-all hover:-translate-y-0.5 hover:shadow-lg hover:brightness-110",
          theme.tileClassName,
        )}
      >
        {/* Modules with a real icon designed for them show it here instead
            of their plain number — see module-theme.ts. Sized to about 2/3
            of the tile's height (h-36) and centered in the space above the
            title. */}
        <div className="flex flex-1 items-center justify-center">
          {Icon ? (
            <Icon className="size-24" aria-hidden="true" />
          ) : (
            <span className="text-3xl font-bold" aria-hidden="true">
              {number}
            </span>
          )}
        </div>
        <span className="text-center text-sm font-semibold">{module.name}</span>
      </div>
    </Link>
  );
}
