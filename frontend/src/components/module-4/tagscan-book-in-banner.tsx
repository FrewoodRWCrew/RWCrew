"use client";

// The "scans waiting to be booked in" message at the top of every
// StockMaster screen, in StockMaster's own soft teal (see lib/module-theme.ts),
// rendered by the module's layout: how many TagScan lines with the action
// "Book In" still wait to go into Inboeken. Hidden when nothing is waiting.
// Clicking it opens TagscanBookInDialog. The same pattern as TagScan's own
// pending-actions banner (components/module-1/pending-actions-banner.tsx).
//
// The count is re-fetched on every page change inside the module, after a
// booking (STOCK_CHANGED_EVENT), and every RECOUNT_INTERVAL_MS, since the
// automatic background Scan in TagScan adds lines without any page action.
//
// Arriving with ?tagscan=open (the landing page's "work waiting" hint)
// opens the dialog straight away; Inboeken's "Load from scan" button opens
// it with TAGSCAN_BOOK_IN_OPEN_EVENT.

import { useCallback, useEffect, useState } from "react";
import { ChevronRight, ScanLine } from "lucide-react";
import { useTranslations } from "next-intl";
import { useSearchParams } from "next/navigation";
import { usePathname } from "@/i18n/navigation";
import { getStockMasterTagscanBookInCount } from "@/lib/api";
import { getModuleTheme } from "@/lib/module-theme";
import { cn } from "@/lib/utils";
import { STOCK_CHANGED_EVENT } from "@/components/module-4/stockmaster-common";
import { TagscanBookInDialog } from "@/components/module-4/tagscan-book-in-dialog";

/** Window event that opens the dialog (Inboeken's "Load from scan" button). */
export const TAGSCAN_BOOK_IN_OPEN_EVENT = "stockmaster:open-tagscan-book-in";

/** Ask the banner to open its dialog. */
export function openTagscanBookInDialog() {
  window.dispatchEvent(new Event(TAGSCAN_BOOK_IN_OPEN_EVENT));
}

// StockMaster's soft tint (background + text) and solid accent (border + icon).
const { badgeClassName, accentColorToken } = getModuleTheme("module-4");
const ACCENT_COLOR = `var(--color-${accentColorToken})`;

/** How often the count is refreshed while a StockMaster screen is open. */
const RECOUNT_INTERVAL_MS = 30_000;

interface TagscanBookInBannerProps {
  /** Whether the user may book in (the dialog fills Inboeken's basket);
   * without it the message still shows, but can't be opened.
   */
  canOpen: boolean;
}

export function TagscanBookInBanner({ canOpen }: TagscanBookInBannerProps) {
  const t = useTranslations("stockMaster.tagscanBookIn");
  const pathname = usePathname();
  const searchParams = useSearchParams();

  const [count, setCount] = useState(0);
  // Read once on arrival: open right away when sent here to review.
  const [isDialogOpen, setIsDialogOpen] = useState(() => canOpen && searchParams.get("tagscan") === "open");
  // Bumped on every open, so the dialog remounts with a clean slate.
  const [dialogKey, setDialogKey] = useState(0);

  const refreshCount = useCallback(() => {
    getStockMasterTagscanBookInCount()
      .then((result) => setCount(result.count))
      // A failed count just hides the banner; the screens show their own errors.
      .catch(() => setCount(0));
  }, []);

  const openDialog = useCallback(() => {
    setDialogKey((current) => current + 1);
    setIsDialogOpen(true);
  }, []);

  // On every page change within the module.
  useEffect(() => {
    refreshCount();
  }, [pathname, refreshCount]);

  // After a booking (it may have used scanned lines).
  useEffect(() => {
    window.addEventListener(STOCK_CHANGED_EVENT, refreshCount);
    return () => window.removeEventListener(STOCK_CHANGED_EVENT, refreshCount);
  }, [refreshCount]);

  // When Inboeken's "Load from scan" button asks for the dialog.
  useEffect(() => {
    if (!canOpen) return;
    window.addEventListener(TAGSCAN_BOOK_IN_OPEN_EVENT, openDialog);
    return () => window.removeEventListener(TAGSCAN_BOOK_IN_OPEN_EVENT, openDialog);
  }, [canOpen, openDialog]);

  // Regularly, for lines added by TagScan's automatic background Scan.
  useEffect(() => {
    const timer = window.setInterval(refreshCount, RECOUNT_INTERVAL_MS);
    return () => window.clearInterval(timer);
  }, [refreshCount]);

  return (
    <>
      {count > 0 && (
        <button
          type="button"
          disabled={!canOpen}
          onClick={openDialog}
          className={cn(
            "mb-4 flex w-full items-center gap-3 rounded-md border px-4 py-3 text-left text-sm font-medium transition-[filter] hover:brightness-95 disabled:cursor-default disabled:hover:brightness-100",
            badgeClassName,
          )}
          style={{
            borderColor: `color-mix(in oklab, ${ACCENT_COLOR} 40%, transparent)`,
          }}
        >
          <ScanLine className="size-5 shrink-0" style={{ color: ACCENT_COLOR }} />
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
        <TagscanBookInDialog
          key={dialogKey}
          open={isDialogOpen}
          onOpenChange={setIsDialogOpen}
          onChanged={refreshCount}
        />
      )}
    </>
  );
}
