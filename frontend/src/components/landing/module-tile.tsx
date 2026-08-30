// One tile on the landing page, representing a single module. All 9
// tiles are always shown, so the overall layout stays stable — but a
// tile only behaves as a clickable link if the current user has been
// granted access to that module; otherwise it's shown locked/greyed out.
// The whole tile is filled with the module's own accent colour (see
// module-theme.ts), not just a small badge, so each module reads clearly
// at a glance.

import { Lock } from "lucide-react";
import { Link } from "@/i18n/navigation";
import { cn } from "@/lib/utils";
import { getModuleNumber, getModuleTheme } from "@/lib/module-theme";
import type { ModuleInfo } from "@/lib/types";

interface ModuleTileProps {
  module: ModuleInfo;
  hasAccess: boolean;
}

export function ModuleTile({ module, hasAccess }: ModuleTileProps) {
  const theme = getModuleTheme(module.key);
  const number = getModuleNumber(module.key);
  const Icon = theme.icon;

  const tileContent = (
    <div
      className={cn(
        "relative flex h-36 flex-col rounded-xl p-4 shadow-sm transition-all",
        theme.tileClassName,
        hasAccess ? "hover:-translate-y-0.5 hover:shadow-lg hover:brightness-110" : "opacity-50",
      )}
    >
      {/* Locked tiles show a padlock badge in the corner instead of next
          to the (now centered) title. */}
      {!hasAccess && (
        <Lock className="absolute top-4 right-4 size-4" aria-hidden="true" />
      )}
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
  );

  if (!hasAccess) {
    // Not a link at all when the user has no access, so it can't
    // accidentally be opened (the backend would reject it anyway, but
    // hiding the link avoids a confusing "access denied" click-through).
    return <div aria-disabled="true">{tileContent}</div>;
  }

  return (
    <Link href={`/modules/${module.key}`} className="block">
      {tileContent}
    </Link>
  );
}
