"use client";

// The phone home page's module tiles: two big coloured squares per row,
// each with the module's icon and name, opening that module's phone screens.
//
// Same rule as the desktop's module-tile.tsx: a module only opens once a year
// is chosen in the year picker above (phone-season-select.tsx). Without one,
// a tile is a plain button that shows a popup instead. This only applies
// while there are open years to choose from, so nobody is locked out when
// there are none.

import { useState } from "react";
import { useTranslations } from "next-intl";
import { Link } from "@/i18n/navigation";
import { getModuleNumber, getModuleTheme } from "@/lib/module-theme";
import type { ModuleInfo } from "@/lib/types";
import { cn } from "@/lib/utils";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { useSelectedSeason } from "@/components/shared/season-provider";
import { phoneModuleHref } from "@/components/phone/shared/phone-modules";

const TILE_CLASS_NAME =
  "flex h-40 w-full flex-col items-center justify-center gap-3 rounded-xl p-3 shadow-sm active:brightness-90";

export function PhoneTileGrid({ modules }: { modules: ModuleInfo[] }) {
  const t = useTranslations("seasonSelector");
  const { seasons, selectedSeasonId } = useSelectedSeason();
  const [showSeasonRequired, setShowSeasonRequired] = useState(false);

  // Opening a module needs a year, unless there's none to choose from.
  const needsSeason = seasons.length > 0 && selectedSeasonId === null;

  return (
    <>
      <div className="grid grid-cols-2 gap-4">
        {modules.map((module) => {
          const theme = getModuleTheme(module.key);
          const Icon = theme.icon;
          const content = (
            <>
              {/* Modules without a designed icon show their number instead. */}
              {Icon ? (
                <Icon className="size-16" aria-hidden="true" />
              ) : (
                <span className="text-4xl font-bold">{getModuleNumber(module.key)}</span>
              )}
              <span className="text-center text-sm font-semibold">{module.name}</span>
            </>
          );

          // No year chosen yet: a button (not a link) that explains why.
          if (needsSeason) {
            return (
              <button
                key={module.key}
                type="button"
                className={cn(TILE_CLASS_NAME, theme.tileClassName)}
                onClick={() => setShowSeasonRequired(true)}
              >
                {content}
              </button>
            );
          }

          return (
            <Link key={module.key} href={phoneModuleHref(module.key)} className={cn(TILE_CLASS_NAME, theme.tileClassName)}>
              {content}
            </Link>
          );
        })}
      </div>

      {/* "Please select a year" popup. */}
      <AlertDialog open={showSeasonRequired} onOpenChange={setShowSeasonRequired}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>{t("requiredTitle")}</AlertDialogTitle>
            <AlertDialogDescription>{t("required")}</AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogAction onClick={() => setShowSeasonRequired(false)}>{t("requiredOk")}</AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  );
}
