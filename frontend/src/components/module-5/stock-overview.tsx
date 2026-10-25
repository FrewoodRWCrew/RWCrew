"use client";

// Atelier's "Stock > Stock" screen: per article and size how many pieces
// are available, waiting to be washed and handed out, with the total and the
// minimum stock. A size below its minimum is marked orange; "?below=1" (the
// minimum-stock banner's link) starts with only those rows. Search on
// article name/code.

import { Fragment, useState } from "react";
import { useTranslations } from "next-intl";
import { useSearchParams } from "next/navigation";
import type { AtelierStockArticle } from "@/lib/types";
import { cn } from "@/lib/utils";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { ArticleThumb } from "@/components/module-5/article-management";

interface StockOverviewProps {
  articles: AtelierStockArticle[];
}

export function StockOverview({ articles }: StockOverviewProps) {
  const t = useTranslations("atelier.stock");
  const tFit = useTranslations("atelier.fits");
  const [search, setSearch] = useState("");
  const [onlyBelow, setOnlyBelow] = useState(useSearchParams().get("below") === "1");

  const isBelow = (size: AtelierStockArticle["sizes"][number]) =>
    size.min_stock !== null && size.active && size.available < size.min_stock;
  const needle = search.trim().toLowerCase();

  // The articles to show, each with only its matching sizes.
  const shown = articles
    .filter((article) => !needle || article.name.toLowerCase().includes(needle) || article.code.toLowerCase().includes(needle))
    .map((article) => ({ ...article, sizes: onlyBelow ? article.sizes.filter(isBelow) : article.sizes }))
    .filter((article) => article.sizes.length > 0);

  const totals = shown.reduce(
    (sum, article) => {
      for (const size of article.sizes) {
        sum.available += size.available;
        sum.toWash += size.to_wash;
        sum.handedOut += size.handed_out;
      }
      return sum;
    },
    { available: 0, toWash: 0, handedOut: 0 },
  );

  return (
    <div className="flex flex-col gap-4">
      <div>
        <h1 className="text-2xl font-bold tracking-tight underline">{t("overview.title")}</h1>
        <p className="text-muted-foreground">{t("overview.description")}</p>
      </div>

      <div className="flex flex-wrap items-center gap-4">
        <Input
          className="w-72"
          placeholder={t("overview.search")}
          value={search}
          onChange={(event) => setSearch(event.target.value)}
        />
        <div className="flex items-center gap-2">
          <Checkbox id="atelier-stock-below" checked={onlyBelow} onCheckedChange={(checked) => setOnlyBelow(checked === true)} />
          <label htmlFor="atelier-stock-below" className="text-sm">
            {t("overview.onlyBelow")}
          </label>
        </div>
        <p className="ml-auto text-sm text-muted-foreground">
          {t("overview.totals", { available: totals.available, toWash: totals.toWash, handedOut: totals.handedOut })}
        </p>
      </div>

      <div className="rounded-md border [&>div]:max-h-[65vh] [&>div]:overflow-y-auto">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="sticky top-0 z-20 bg-background font-bold underline">{t("columns.article")}</TableHead>
              <TableHead className="sticky top-0 z-20 bg-background font-bold underline">{t("columns.size")}</TableHead>
              <TableHead className="sticky top-0 z-20 bg-background text-right font-bold underline">
                {t("statuses.available")}
              </TableHead>
              <TableHead className="sticky top-0 z-20 bg-background text-right font-bold underline">
                {t("statuses.to_wash")}
              </TableHead>
              <TableHead className="sticky top-0 z-20 bg-background text-right font-bold underline">
                {t("statuses.handed_out")}
              </TableHead>
              <TableHead className="sticky top-0 z-20 bg-background text-right font-bold underline">
                {t("columns.total")}
              </TableHead>
              <TableHead className="sticky top-0 z-20 bg-background text-right font-bold underline">
                {t("columns.minStock")}
              </TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {shown.length === 0 && (
              <TableRow>
                <TableCell colSpan={7} className="text-center text-muted-foreground">
                  {t("overview.empty")}
                </TableCell>
              </TableRow>
            )}
            {shown.map((article) => (
              <Fragment key={article.article_id}>
                {article.sizes.map((size, index) => {
                  const below = isBelow(size);
                  return (
                    <TableRow key={size.article_size_id} className={below ? "bg-orange-50 dark:bg-orange-500/10" : undefined}>
                      <TableCell>
                        {/* The article only on its first size row. */}
                        {index === 0 && (
                          <div className="flex items-center gap-3">
                            <ArticleThumb article={{ id: article.article_id, ...article }} />
                            <div>
                              <p className={cn("font-medium", !article.active && "italic")}>{article.name}</p>
                              <p className="font-mono text-xs text-muted-foreground">{article.code}</p>
                            </div>
                          </div>
                        )}
                      </TableCell>
                      <TableCell className={size.active ? undefined : "text-muted-foreground italic"}>
                        {size.size_name} · {tFit(size.fit)}
                      </TableCell>
                      <TableCell className={cn("text-right font-medium", below && "text-orange-700 dark:text-orange-300")}>
                        {size.available}
                      </TableCell>
                      <TableCell className="text-right">{size.to_wash}</TableCell>
                      <TableCell className="text-right">{size.handed_out}</TableCell>
                      <TableCell className="text-right font-bold">
                        {size.available + size.to_wash + size.handed_out}
                      </TableCell>
                      <TableCell className="text-right text-muted-foreground">{size.min_stock ?? ""}</TableCell>
                    </TableRow>
                  );
                })}
              </Fragment>
            ))}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}
