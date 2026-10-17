"use client";

// KarLoadHeader, on top of Kar laden's booking screen for one kar: the kar as
// a header block (number, team, in the warehouse or out, how many product
// types and pieces are loaded, and an X to pick another kar). It reads the kar
// detail the panel refreshes after every booking, so it updates right away.
// (The kar's products are in the "Karinhoud" table, kar-load-table.tsx.)

import { X } from "lucide-react";
import { useTranslations } from "next-intl";
import type { StockMasterKarDetail } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { KarStatusBadge } from "@/components/module-4/stock-pickers";

/** The chosen kar as a header block, with its loading progress. */
export function KarLoadHeader({ detail, onClear }: { detail: StockMasterKarDetail; onClear: () => void }) {
  const t = useTranslations("stockMaster");
  const kar = detail.kar;
  const hasNeeds = kar.required_product_count > 0;
  const complete = hasNeeds && kar.loaded_product_count >= kar.required_product_count;
  const percent = hasNeeds ? Math.round((kar.loaded_product_count / kar.required_product_count) * 100) : 0;

  return (
    <div className="flex flex-wrap items-center gap-x-6 gap-y-3 rounded-xl border-2 border-primary/40 bg-primary/5 px-5 py-4">
      {/* Kar number, team and where it is. */}
      <div className="flex min-w-0 flex-col gap-1">
        <div className="flex flex-wrap items-center gap-3">
          <span className="text-3xl font-bold tracking-tight">{kar.kar_nummer}</span>
          <KarStatusBadge isOut={kar.is_out} />
        </div>
        <span className="text-muted-foreground">{kar.team_name ?? t("common.noTeam")}</span>
      </div>

      {/* Loading progress: product types (bar, green when complete) and pieces. */}
      <div className="ml-auto flex items-center gap-3">
        {hasNeeds ? (
          <div className="flex w-64 flex-col gap-1">
            <div className="flex justify-between text-sm tabular-nums">
              <span className="font-medium">
                {t("karLoadOverview.productsCount", { done: kar.loaded_product_count, total: kar.required_product_count })}
              </span>
              <span className="text-muted-foreground">
                {t("karLoadOverview.piecesCount", { done: kar.loaded_toward_required, total: kar.required_total })}
              </span>
            </div>
            <div
              className="h-2 overflow-hidden rounded-full bg-muted"
              role="progressbar"
              aria-valuemin={0}
              aria-valuemax={kar.required_product_count}
              aria-valuenow={kar.loaded_product_count}
            >
              <div className={complete ? "h-full bg-green-600" : "h-full bg-primary"} style={{ width: `${percent}%` }} />
            </div>
          </div>
        ) : (
          <span className="text-sm text-muted-foreground">{t("karLoadOverview.noNeeds")}</span>
        )}
        <Button variant="ghost" size="icon-sm" onClick={onClear} aria-label={t("common.changeKar")} title={t("common.changeKar")}>
          <X />
        </Button>
      </div>
    </div>
  );
}
