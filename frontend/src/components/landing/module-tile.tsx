"use client";

// One tile on the landing page, representing a single module. The
// landing page only ever passes in modules the current user has access
// to (see page.tsx), so every tile rendered here is always a clickable
// link — no locked/greyed-out state to handle. The whole tile is filled
// with the module's own accent colour (see module-theme.ts), not just a
// small badge, so each module reads clearly at a glance.
//
// A module can only be opened once a season is chosen in the header's
// season selector; without one, the tile is a plain button (not a link, so
// middle-click / "open in new tab" can't get around it either) that shows
// a popup instead.
// This only applies while the selector is actually shown (there are open
// seasons to pick from), so nobody gets locked out when there are none,
// and not to the "Mobile App" install page, which has no season.

import { useState } from "react";
import { useTranslations } from "next-intl";
import { Link } from "@/i18n/navigation";
import { cn } from "@/lib/utils";
import { getModuleNumber, getModuleTheme } from "@/lib/module-theme";
import type { ModuleInfo } from "@/lib/types";
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

// The phone-app install page doesn't work per season.
const SEASONLESS_MODULE_KEYS = new Set(["module-10"]);

interface ModuleTileProps {
  module: ModuleInfo;
  /** Renders the tile at about half its normal size — used for the "Mobile
   *  App" shortcut, which isn't a real module and so sits outside the grid. */
  compact?: boolean;
}

export function ModuleTile({ module, compact = false }: ModuleTileProps) {
  const theme = getModuleTheme(module.key);
  const number = getModuleNumber(module.key);
  const Icon = theme.icon;
  const t = useTranslations("seasonSelector");
  const { seasons, selectedSeasonId } = useSelectedSeason();
  const [showSeasonRequired, setShowSeasonRequired] = useState(false);

  // Opening needs a season, unless there's none to choose or the module has no seasons.
  const needsSeason = seasons.length > 0 && selectedSeasonId === null && !SEASONLESS_MODULE_KEYS.has(module.key);

  const tile = (
    <div
      className={cn(
        "relative flex flex-col rounded-xl shadow-sm transition-all hover:-translate-y-0.5 hover:shadow-lg hover:brightness-110",
        // Every size scales down together in compact mode.
        compact ? "h-18 p-2" : "h-36 p-4",
        theme.tileClassName,
      )}
    >
      {/* Modules with a real icon designed for them show it here instead
          of their plain number — see module-theme.ts. Sized to about 2/3
          of the tile's height and centered in the space above the
          title. */}
      <div className="flex flex-1 items-center justify-center">
        {Icon ? (
          <Icon className={compact ? "size-10" : "size-24"} aria-hidden="true" />
        ) : (
          <span className={cn("font-bold", compact ? "text-xl" : "text-3xl")} aria-hidden="true">
            {number}
          </span>
        )}
      </div>
      <span className={cn("text-center font-semibold", compact ? "text-xs" : "text-sm")}>{module.name}</span>
    </div>
  );

  if (!needsSeason) {
    return (
      <Link href={`/modules/${module.key}`} className="block">
        {tile}
      </Link>
    );
  }

  return (
    <>
      <button
        type="button"
        className="block w-full cursor-pointer text-left"
        onClick={() => setShowSeasonRequired(true)}
      >
        {tile}
      </button>

      {/* "Please select a season" popup. */}
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
