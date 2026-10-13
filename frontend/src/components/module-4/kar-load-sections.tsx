"use client";

// The two kar blocks of Kar laden's booking screen for one kar:
// - KarLoadHeader, on top: the kar as a header block (number, team, in the
//   warehouse or out, how many product types and pieces are loaded, and an X
//   to pick another kar);
// - KarContentsSection, under the basket ("Nog te laden"): "Inhoud in kar",
//   what's in the kar now, with its picture and the need (list-screen table
//   pattern: pinned header, capped scroll box).
// Both read the kar detail the panel refreshes after every booking, so they
// update right away.

import { X } from "lucide-react";
import { useTranslations } from "next-intl";
import type { StockMasterKarDetail, StockMasterKarLine, StockMasterProductStock } from "@/lib/types";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { ProductThumb } from "@/components/module-4/product-thumb";
import { KarStatusBadge } from "@/components/module-4/stock-pickers";

// Sticky header cell classes of the list (bold + underlined, opaque while scrolling).
const HEAD = "sticky top-0 z-20 bg-background font-bold underline";

interface KarContentsSectionProps {
  detail: StockMasterKarDetail;
  /** The panel's stock rows, for the product pictures. */
  productsById: Map<number, StockMasterProductStock>;
}

/** "Inhoud in kar": what's in the kar now, framed like the kar header but on a plain background. */
export function KarContentsSection({ detail, productsById }: KarContentsSectionProps) {
  const t = useTranslations("stockMaster");
  const inKar = detail.lines.filter((line) => line.in_kar > 0);

  return (
    <section className="flex flex-col gap-2 rounded-xl border-2 border-primary/40 bg-background px-5 py-4">
      <h2 className="text-lg font-semibold">{t("karLoad.contentsTitle")}</h2>
      {inKar.length === 0 ? (
        <p className="text-sm text-muted-foreground">{t("karLoad.emptyKar")}</p>
      ) : (
        // No border of its own: the frame around the section is enough.
        <div className="[&>div]:max-h-[40vh] [&>div]:overflow-y-auto">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className={cn(HEAD, "w-14")}>
                  <span className="sr-only">{t("karLoad.picture")}</span>
                </TableHead>
                <TableHead className={HEAD}>{t("common.product")}</TableHead>
                <TableHead className={HEAD}>{t("common.bin")}</TableHead>
                <TableHead className={cn(HEAD, "text-right")}>{t("kars.needed")}</TableHead>
                <TableHead className={cn(HEAD, "text-right")}>{t("kars.inKar")}</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {inKar.map((line) => (
                <TableRow key={line.product_id}>
                  <TableCell>
                    <ProductThumb productId={line.product_id} name={line.name} product={productsById.get(line.product_id)} />
                  </TableCell>
                  <TableCell className="font-medium">{line.name}</TableCell>
                  <BinCell line={line} />
                  <TableCell className="text-right tabular-nums">{line.required || ""}</TableCell>
                  <TableCell className="text-right tabular-nums">
                    <span className="font-semibold">{line.in_kar}</span>
                    {/* More in the kar than needed. */}
                    {line.surplus > 0 && (
                      <span className="ml-2 text-xs text-muted-foreground">
                        {t("kars.surplus", { count: line.surplus })}
                      </span>
                    )}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}
    </section>
  );
}

/** A product's bin, or "geen locatie". */
function BinCell({ line }: { line: StockMasterKarLine }) {
  const t = useTranslations("stockMaster");
  return <TableCell className="text-muted-foreground">{line.bin_label ?? t("common.noBin")}</TableCell>;
}

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
