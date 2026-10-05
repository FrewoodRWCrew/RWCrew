"use client";

// The product and kar search boxes used on StockMaster's booking, count
// and needs screens, built on Typeahead. A product match shows its bin and
// current stock ("Walkie-lader · Hal A · B-12 · vrij 5"); a kar match shows
// its team and whether it's in the warehouse or out.

import { forwardRef } from "react";
import { X } from "lucide-react";
import { useTranslations } from "next-intl";
import type { StockMasterKarSummary, StockMasterProductStock } from "@/lib/types";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Typeahead } from "@/components/module-4/typeahead";

interface ProductSearchProps {
  products: StockMasterProductStock[];
  onSelect: (product: StockMasterProductStock) => void;
  /** Blocked products can't be booked in or loaded. */
  blockBlocked?: boolean;
  /** Show this kar's stock of each product next to the free stock. */
  karId?: number | null;
  autoFocus?: boolean;
  disabled?: boolean;
  id?: string;
}

export const ProductSearch = forwardRef<HTMLInputElement, ProductSearchProps>(function ProductSearch(
  { products, onSelect, blockBlocked, karId, autoFocus, disabled, id },
  ref,
) {
  const t = useTranslations("stockMaster.common");
  return (
    <Typeahead
      id={id}
      ref={ref}
      items={products}
      getKey={(product) => product.product_id}
      getText={(product) => product.name}
      onSelect={onSelect}
      placeholder={t("productSearchPlaceholder")}
      emptyText={t("noMatches")}
      autoFocus={autoFocus}
      disabled={disabled}
      isDisabled={(product) => Boolean(blockBlocked && product.is_blocked)}
      renderItem={(product) => {
        const inKar = karId ? (product.kars.find((kar) => kar.kar_id === karId)?.quantity ?? 0) : null;
        return (
          <div className="flex items-center justify-between gap-3">
            <div className="min-w-0">
              <div className="truncate font-medium">{product.name}</div>
              <div className="truncate text-xs text-muted-foreground">{product.bin_label ?? t("noBin")}</div>
            </div>
            <div className="flex shrink-0 items-center gap-2 text-xs tabular-nums">
              {product.is_blocked && <Badge variant="destructive">{t("blocked")}</Badge>}
              <span>{t("freeShort", { count: product.free })}</span>
              {inKar !== null && <span className="text-muted-foreground">{t("inKarShort", { count: inKar })}</span>}
            </div>
          </div>
        );
      }}
    />
  );
});

interface KarSearchProps {
  kars: StockMasterKarSummary[];
  onSelect: (kar: StockMasterKarSummary) => void;
  /** Kars that can't be picked here (e.g. out of the warehouse). */
  isDisabled?: (kar: StockMasterKarSummary) => boolean;
  autoFocus?: boolean;
  id?: string;
}

export function KarSearch({ kars, onSelect, isDisabled, autoFocus, id }: KarSearchProps) {
  const t = useTranslations("stockMaster.common");
  return (
    <Typeahead
      id={id}
      items={kars}
      getKey={(kar) => kar.kar_id}
      getText={(kar) => kar.kar_nummer}
      onSelect={onSelect}
      placeholder={t("karSearchPlaceholder")}
      emptyText={t("noMatches")}
      autoFocus={autoFocus}
      isDisabled={isDisabled}
      renderItem={(kar) => (
        <div className="flex items-center justify-between gap-3">
          <div className="min-w-0">
            <span className="font-semibold">{kar.kar_nummer}</span>
            <span className="ml-2 text-xs text-muted-foreground">{kar.team_name ?? t("noTeam")}</span>
          </div>
          <KarStatusBadge isOut={kar.is_out} />
        </div>
      )}
    />
  );
}

/** "In magazijn" (green) or "Onderweg" (orange). */
export function KarStatusBadge({ isOut }: { isOut: boolean }) {
  const t = useTranslations("stockMaster.common");
  return isOut ? (
    <Badge className="bg-orange-100 text-orange-800 dark:bg-orange-500/15 dark:text-orange-300">{t("karOut")}</Badge>
  ) : (
    <Badge className="bg-green-100 text-green-800 dark:bg-green-500/15 dark:text-green-300">{t("karIn")}</Badge>
  );
}

/** The chosen kar, with a button to pick another one. */
export function SelectedKar({ kar, onClear }: { kar: StockMasterKarSummary; onClear?: () => void }) {
  const t = useTranslations("stockMaster.common");
  return (
    <div className="flex items-center gap-3 rounded-md border bg-muted/40 px-3 py-2">
      <span className="text-lg font-semibold">{kar.kar_nummer}</span>
      <span className="text-sm text-muted-foreground">{kar.team_name ?? t("noTeam")}</span>
      <KarStatusBadge isOut={kar.is_out} />
      {onClear && (
        <Button variant="ghost" size="icon-sm" className="ml-auto" onClick={onClear} aria-label={t("changeKar")}>
          <X />
        </Button>
      )}
    </div>
  );
}
