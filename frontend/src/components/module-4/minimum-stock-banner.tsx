"use client";

// The orange message at the top of every StockMaster screen (rendered by
// the module's layout) when consumables are below their minimum stock:
// "3 producten onder minimum stock". Clicking it opens the stock overview
// filtered on those products. Hidden when nothing is below its minimum.
//
// The count is re-fetched on every page change inside the module and after
// a booking (screens dispatch STOCK_CHANGED_EVENT) — the same approach as
// TagScan's pending-actions banner.

import { useCallback, useEffect, useState } from "react";
import { ChevronRight, TriangleAlert } from "lucide-react";
import { useTranslations } from "next-intl";
import { Link, usePathname } from "@/i18n/navigation";
import { getStockMasterAlerts } from "@/lib/api";
import { STOCK_CHANGED_EVENT, STOCKMASTER_BASE } from "@/components/module-4/stockmaster-common";

interface MinimumStockBannerProps {
  /** Whether the user can open the stock overview the banner links to. */
  canOpen: boolean;
}

export function MinimumStockBanner({ canOpen }: MinimumStockBannerProps) {
  const t = useTranslations("stockMaster.banner");
  const pathname = usePathname();
  const [count, setCount] = useState(0);

  const refreshCount = useCallback(() => {
    getStockMasterAlerts()
      .then((result) => setCount(result.below_minimum_count))
      // A failed count just hides the banner; the screens show their own errors.
      .catch(() => setCount(0));
  }, []);

  // On every page change within the module.
  useEffect(() => {
    refreshCount();
  }, [pathname, refreshCount]);

  // After a booking on the same page.
  useEffect(() => {
    window.addEventListener(STOCK_CHANGED_EVENT, refreshCount);
    return () => window.removeEventListener(STOCK_CHANGED_EVENT, refreshCount);
  }, [refreshCount]);

  if (count === 0) return null;

  const content = (
    <>
      <TriangleAlert className="size-5 shrink-0" aria-hidden="true" />
      <span className="flex-1 font-medium">{t("message", { count })}</span>
      {canOpen && (
        <span className="flex items-center gap-1 text-sm underline">
          {t("open")}
          <ChevronRight className="size-4" aria-hidden="true" />
        </span>
      )}
    </>
  );
  const className =
    "mb-4 flex items-center gap-3 rounded-md border border-orange-300 bg-orange-50 px-4 py-3 text-orange-800 dark:border-orange-500/40 dark:bg-orange-500/10 dark:text-orange-200";

  return canOpen ? (
    <Link href={`${STOCKMASTER_BASE}/stock?below=1`} className={`${className} hover:bg-orange-100 dark:hover:bg-orange-500/20`}>
      {content}
    </Link>
  ) : (
    <div className={className}>{content}</div>
  );
}
