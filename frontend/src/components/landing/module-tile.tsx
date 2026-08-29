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

  const tileContent = (
    <div
      className={cn(
        "flex h-36 flex-col justify-between rounded-xl p-4 shadow-sm transition-all",
        theme.tileClassName,
        hasAccess ? "hover:-translate-y-0.5 hover:shadow-lg hover:brightness-110" : "opacity-50",
      )}
    >
      <span className="text-3xl font-bold" aria-hidden="true">
        {number}
      </span>
      <div className="flex items-center justify-between">
        <span className="text-sm font-semibold">{module.name}</span>
        {!hasAccess && <Lock className="size-4" aria-hidden="true" />}
      </div>
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
