// The phone home page's module tiles: two big coloured squares per row,
// each with the module's icon and name, opening that module's phone screens.

import { Link } from "@/i18n/navigation";
import { getModuleNumber, getModuleTheme } from "@/lib/module-theme";
import type { ModuleInfo } from "@/lib/types";
import { cn } from "@/lib/utils";
import { phoneModuleHref } from "@/components/phone/shared/phone-modules";

export function PhoneTileGrid({ modules }: { modules: ModuleInfo[] }) {
  return (
    <div className="grid grid-cols-2 gap-4">
      {modules.map((module) => {
        const theme = getModuleTheme(module.key);
        const Icon = theme.icon;
        return (
          <Link
            key={module.key}
            href={phoneModuleHref(module.key)}
            className={cn(
              "flex h-40 flex-col items-center justify-center gap-3 rounded-xl p-3 shadow-sm active:brightness-90",
              theme.tileClassName,
            )}
          >
            {/* Modules without a designed icon show their number instead. */}
            {Icon ? (
              <Icon className="size-16" aria-hidden="true" />
            ) : (
              <span className="text-4xl font-bold">{getModuleNumber(module.key)}</span>
            )}
            <span className="text-center text-sm font-semibold">{module.name}</span>
          </Link>
        );
      })}
    </div>
  );
}
