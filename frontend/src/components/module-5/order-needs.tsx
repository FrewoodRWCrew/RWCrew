"use client";

// Atelier's "Stock > Te bestellen" screen: per article size what to buy for
// the chosen season — the highest estimated need on one festival day (persons
// × package, split by the article's size split) minus everything the atelier
// owns (available + to wash + handed out). Only sizes that fall short are
// listed; "Afdrukken" opens the same list as a PDF.

import { Printer } from "lucide-react";
import { useLocale, useTranslations } from "next-intl";
import { atelierOrderNeedsPdfUrl, getAtelierOrderNeeds } from "@/lib/api";
import type { AtelierOrderNeed, Season } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Table, TableBody, TableCell, TableFooter, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { AtelierSeasonSelect, useAtelierSeasonId } from "@/components/module-5/atelier-season-select";
import { useKeyedLoad } from "@/components/module-4/use-keyed-load";

interface OrderNeedsProps {
  seasons: Season[];
}

export function OrderNeeds({ seasons }: OrderNeedsProps) {
  const t = useTranslations("atelier.stock");
  const tFit = useTranslations("atelier.fits");
  const locale = useLocale();
  const seasonId = useAtelierSeasonId(seasons);
  const needs = useKeyedLoad<AtelierOrderNeed[]>(seasonId === null ? null : String(seasonId), () =>
    getAtelierOrderNeeds(seasonId!),
  );
  const lines = needs.data ?? [];

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight underline">{t("orderNeeds.title")}</h1>
          <p className="text-muted-foreground">{t("orderNeeds.description")}</p>
        </div>
        <div className="flex items-end gap-3">
          <Button
            variant="outline"
            disabled={seasonId === null}
            onClick={() => seasonId !== null && window.open(atelierOrderNeedsPdfUrl(seasonId, locale), "_blank")}
          >
            <Printer className="size-4" />
            {t("orderNeeds.print")}
          </Button>
          <AtelierSeasonSelect seasons={seasons} seasonId={seasonId} />
        </div>
      </div>

      <div className="rounded-md border [&>div]:max-h-[65vh] [&>div]:overflow-y-auto">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="sticky top-0 z-20 bg-background font-bold underline">{t("columns.article")}</TableHead>
              <TableHead className="sticky top-0 z-20 bg-background font-bold underline">{t("columns.size")}</TableHead>
              <TableHead className="sticky top-0 z-20 bg-background text-right font-bold underline">{t("orderNeeds.needed")}</TableHead>
              <TableHead className="sticky top-0 z-20 bg-background font-bold underline">{t("orderNeeds.festival")}</TableHead>
              <TableHead className="sticky top-0 z-20 bg-background text-right font-bold underline">{t("orderNeeds.owned")}</TableHead>
              <TableHead className="sticky top-0 z-20 bg-background text-right font-bold underline">{t("orderNeeds.toOrder")}</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {lines.length === 0 && (
              <TableRow>
                <TableCell colSpan={6} className="text-center text-muted-foreground">
                  {needs.isLoading ? t("loading") : t("orderNeeds.nothing")}
                </TableCell>
              </TableRow>
            )}
            {lines.map((line) => (
              <TableRow key={line.article_size_id}>
                <TableCell>
                  <span className="font-medium">{line.article_name}</span>{" "}
                  <span className="font-mono text-xs text-muted-foreground">{line.article_code}</span>
                </TableCell>
                <TableCell>
                  {line.size_name} · {tFit(line.fit)}
                </TableCell>
                <TableCell className="text-right">{line.needed}</TableCell>
                <TableCell className="text-muted-foreground">{line.festival_name}</TableCell>
                <TableCell className="text-right">{line.owned}</TableCell>
                <TableCell className="text-right font-bold text-destructive">{line.to_order}</TableCell>
              </TableRow>
            ))}
          </TableBody>
          {lines.length > 0 && (
            <TableFooter>
              <TableRow>
                <TableCell colSpan={5} className="font-bold">
                  {t("columns.total")}
                </TableCell>
                <TableCell className="text-right font-bold">{lines.reduce((sum, line) => sum + line.to_order, 0)}</TableCell>
              </TableRow>
            </TableFooter>
          )}
        </Table>
      </div>
    </div>
  );
}
