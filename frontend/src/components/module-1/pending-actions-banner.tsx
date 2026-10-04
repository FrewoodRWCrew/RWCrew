"use client";

// The coloured "actions waiting" message shown at the top of every TagScan
// screen (rendered by the module's layout): how many scanned lines still
// have an action (e.g. "Assignment") that hasn't been carried out. Hidden
// when nothing is waiting. Clicking it opens PendingActionsDialog.
//
// The count is re-fetched on every page change inside the module, after
// the dialog changed something, and whenever another screen announces new
// lines (Tag Headerdata's Scan dispatches PENDING_ACTIONS_CHANGED_EVENT),
// since a scan on the same page doesn't navigate — and every
// RECOUNT_INTERVAL_MS, since the automatic background Scan (Settings) adds
// lines without any page action at all.
//
// Arriving with ?pending=open (the landing page's "work waiting" hint)
// opens the dialog straight away.

import { useCallback, useEffect, useState } from "react";
import { AlertTriangle, ChevronRight } from "lucide-react";
import { useTranslations } from "next-intl";
import { useSearchParams } from "next/navigation";
import { usePathname } from "@/i18n/navigation";
import { getPendingTagActionsCount } from "@/lib/api";
import { PendingActionsDialog } from "@/components/module-1/pending-actions-dialog";

/** Window event a TagScan screen dispatches after it created/changed lines. */
export const PENDING_ACTIONS_CHANGED_EVENT = "tagscan:pending-actions-changed";

/** How often the count is refreshed while a TagScan screen is open. */
const RECOUNT_INTERVAL_MS = 30_000;

interface PendingActionsBannerProps {
  /** Whether the user can see the waiting lines (Tag Linedata view right);
   * without it the message still shows, but can't be opened.
   */
  canOpen: boolean;
}

export function PendingActionsBanner({ canOpen }: PendingActionsBannerProps) {
  const t = useTranslations("tagscan.pendingActions");
  const pathname = usePathname();
  const searchParams = useSearchParams();

  const [count, setCount] = useState(0);
  // Read once on arrival: open right away when sent here to review.
  const [isDialogOpen, setIsDialogOpen] = useState(() => canOpen && searchParams.get("pending") === "open");
  // Bumped on every open, so the dialog remounts with a clean slate.
  const [dialogKey, setDialogKey] = useState(0);

  const refreshCount = useCallback(() => {
    getPendingTagActionsCount()
      .then((result) => setCount(result.count))
      // A failed count just hides the banner; the screens themselves
      // still work and show their own errors.
      .catch(() => setCount(0));
  }, []);

  // On every page change within the module.
  useEffect(() => {
    refreshCount();
  }, [pathname, refreshCount]);

  // When another screen says it changed lines (e.g. a new Scan).
  useEffect(() => {
    window.addEventListener(PENDING_ACTIONS_CHANGED_EVENT, refreshCount);
    return () => window.removeEventListener(PENDING_ACTIONS_CHANGED_EVENT, refreshCount);
  }, [refreshCount]);

  // Regularly, for lines added by the automatic background Scan.
  useEffect(() => {
    const timer = window.setInterval(refreshCount, RECOUNT_INTERVAL_MS);
    return () => window.clearInterval(timer);
  }, [refreshCount]);

  function openDialog() {
    setDialogKey((current) => current + 1);
    setIsDialogOpen(true);
  }

  return (
    <>
      {count > 0 && (
        <button
          type="button"
          disabled={!canOpen}
          onClick={openDialog}
          className="mb-4 flex w-full items-center gap-3 rounded-md border border-orange-500/40 bg-orange-100 px-4 py-3 text-left text-sm font-medium text-orange-900 transition-colors hover:bg-orange-200 disabled:cursor-default disabled:hover:bg-orange-100 dark:bg-orange-500/15 dark:text-orange-300 dark:hover:bg-orange-500/25 dark:disabled:hover:bg-orange-500/15"
        >
          <AlertTriangle className="size-5 shrink-0" />
          <span className="flex-1">{t("bannerText", { count })}</span>
          {canOpen && (
            <span className="flex items-center gap-1 font-semibold underline">
              {t("bannerOpen")}
              <ChevronRight className="size-4" />
            </span>
          )}
        </button>
      )}

      {canOpen && (
        <PendingActionsDialog
          key={dialogKey}
          open={isDialogOpen}
          onOpenChange={setIsDialogOpen}
          onChanged={refreshCount}
        />
      )}
    </>
  );
}
