"use client";

// StockMaster's "you are here" bar, shown above the title of the booking
// screens that belong to the warehouse process: Inboeken → Kar laden →
// Kar vertrekt → Festival → Kar terug → Kar uitladen. The step of the
// current screen is green; the others are grey and link to their screen
// when the user may make that booking. "Festival" has no screen: it only
// marks the time the kar is away. Every block has a tooltip that explains
// its step in more detail (stockMaster.processFlow.help.<step>).

import { useTranslations } from "next-intl";
import { Link } from "@/i18n/navigation";
import type { StockMasterAction, StockMasterMyPermissions } from "@/lib/types";
import { cn } from "@/lib/utils";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";
import { ACTION_PATHS, STOCKMASTER_BASE, canBook } from "@/components/module-4/stockmaster-common";

type FlowStep = StockMasterAction | "festival";

/** The process steps, in order. */
const PROCESS_FLOW: FlowStep[] = ["book_in", "kar_load", "kar_dispatch", "festival", "kar_return", "kar_unload"];

/** Whether a booking screen is part of the process (and so shows the bar). */
export function isProcessFlowAction(action: StockMasterAction): boolean {
  return PROCESS_FLOW.includes(action);
}

interface ProcessFlowProps {
  action: StockMasterAction;
  permissions: StockMasterMyPermissions;
}

export function ProcessFlow({ action, permissions }: ProcessFlowProps) {
  const t = useTranslations("stockMaster");

  return (
    <nav aria-label={t("processFlow.label")}>
      {/* The app has no global tooltip provider: this bar brings its own. */}
      <TooltipProvider delay={200}>
        {/* Scrolls sideways inside itself on narrow screens instead of widening the page. */}
        <ol className="flex items-center overflow-x-auto py-1">
          {PROCESS_FLOW.map((step, index) => {
            const isActive = step === action;
            const label = step === "festival" ? t("processFlow.festival") : t(`actions.${step}.title`);
            const boxClass = cn(
              "block shrink-0 whitespace-nowrap rounded-lg border px-4 py-2 text-sm",
              isActive
                ? "border-green-600 bg-green-500 font-semibold text-white shadow-sm ring-2 ring-green-500/30"
                : step === "festival"
                  ? // The time the kar is away: always purple, set apart from the warehouse steps.
                    "border-purple-600 bg-purple-500 text-white"
                  : "bg-muted text-foreground",
            );
            // Other steps link to their screen when the user may book there.
            const href =
              !isActive && step !== "festival" && canBook(permissions, step)
                ? `${STOCKMASTER_BASE}${ACTION_PATHS[step]}`
                : null;
  
            return (
              <li key={step} className="flex shrink-0 items-center sm:flex-1 sm:last:flex-none">
                {/* Hovering or focusing a block explains that step in more detail. */}
                <Tooltip>
                  <TooltipTrigger
                    render={
                      href ? (
                        <Link href={href} className={cn(boxClass, "transition-colors hover:bg-muted/60 hover:border-foreground/30")} />
                      ) : (
                        // Focusable, so keyboard users can open the explanation too.
                        <span tabIndex={0} className={boxClass} aria-current={isActive ? "step" : undefined} />
                      )
                    }
                  >
                    {label}
                  </TooltipTrigger>
                  <TooltipContent className="text-sm">{t(`processFlow.help.${step}`)}</TooltipContent>
                </Tooltip>
                {/* The line to the next step. */}
                {index < PROCESS_FLOW.length - 1 && <span aria-hidden className="h-px w-6 min-w-6 bg-border sm:flex-1" />}
              </li>
            );
          })}
        </ol>
      </TooltipProvider>
    </nav>
  );
}
