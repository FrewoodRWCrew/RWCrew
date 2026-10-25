"use client";

// Atelier's "Stock > Telling" screen: pick the articles you counted, fill in
// per size the counted pieces available and to wash (pre-filled with the
// booked stock), then book. Only the differences are booked, as one count
// document; pieces handed out aren't counted here (they're at the workers).

import { useState } from "react";
import { Plus, X } from "lucide-react";
import { useTranslations } from "next-intl";
import { toast } from "sonner";
import { bookAtelierCount, listAtelierStock } from "@/lib/api";
import type { AtelierStockArticle } from "@/lib/types";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Textarea } from "@/components/ui/textarea";
import { ATELIER_STOCK_CHANGED_EVENT, atelierStockErrorMessage } from "@/components/module-5/atelier-stock-common";

type Counted = Record<string, number>; // "<article size id>:<status>" -> counted

interface StockCountProps {
  initialStock: AtelierStockArticle[];
  canBook: boolean;
}

export function StockCount({ initialStock, canBook }: StockCountProps) {
  const t = useTranslations("atelier.stock");
  const tFit = useTranslations("atelier.fits");
  const [stock, setStock] = useState(initialStock);
  const [articleIds, setArticleIds] = useState<number[]>([]);
  const [counted, setCounted] = useState<Counted>({});
  const [note, setNote] = useState("");
  const [isBooking, setIsBooking] = useState(false);

  const pickable = stock.filter((article) => !articleIds.includes(article.article_id) && article.sizes.length > 0);
  const chosen = articleIds
    .map((id) => stock.find((article) => article.article_id === id))
    .filter((article): article is AtelierStockArticle => article !== undefined);

  // The counted value shown: what was typed, else the booked stock.
  function valueOf(articleSizeId: number, status: "available" | "to_wash", booked: number) {
    return counted[`${articleSizeId}:${status}`] ?? booked;
  }

  // Every counted cell that differs from the booked stock.
  const differences = chosen.flatMap((article) =>
    article.sizes.flatMap((size) =>
      (["available", "to_wash"] as const)
        .map((status) => {
          const booked = status === "available" ? size.available : size.to_wash;
          return { article_size_id: size.article_size_id, status, counted: valueOf(size.article_size_id, status, booked), booked };
        })
        .filter((line) => line.counted !== line.booked),
    ),
  );

  async function handleBook() {
    setIsBooking(true);
    try {
      const document = await bookAtelierCount({
        lines: differences.map(({ article_size_id, status, counted: value }) => ({ article_size_id, status, counted: value })),
        note: note.trim() || null,
      });
      toast.success(t("booked", { number: document.doc_number, count: document.total_quantity }));
      setStock(await listAtelierStock());
      setCounted({});
      setArticleIds([]);
      setNote("");
      window.dispatchEvent(new Event(ATELIER_STOCK_CHANGED_EVENT));
    } catch (error) {
      toast.error(atelierStockErrorMessage(t, error));
    } finally {
      setIsBooking(false);
    }
  }

  return (
    <div className="flex flex-col gap-4">
      <div>
        <h1 className="text-2xl font-bold tracking-tight underline">{t("count.title")}</h1>
        <p className="text-muted-foreground">{t("count.description")}</p>
      </div>

      <div className="flex w-80 flex-col gap-2">
        <Label>{t("addArticle")}</Label>
        <Select
          value=""
          onValueChange={(value) => value && setArticleIds((current) => [...current, Number(value)])}
          disabled={pickable.length === 0}
        >
          <SelectTrigger>
            <Plus className="size-4" />
            <SelectValue>{() => (pickable.length ? t("pickArticle") : t("nothingToPick"))}</SelectValue>
          </SelectTrigger>
          <SelectContent>
            {pickable.map((article) => (
              <SelectItem key={article.article_id} value={String(article.article_id)}>
                {article.name} ({article.code})
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {chosen.length === 0 ? (
        <p className="text-sm text-muted-foreground">{t("count.empty")}</p>
      ) : (
        <div className="rounded-md border [&>div]:max-h-[60vh] [&>div]:overflow-y-auto">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="sticky top-0 z-20 bg-background font-bold underline">{t("columns.article")}</TableHead>
                <TableHead className="sticky top-0 z-20 bg-background font-bold underline">{t("columns.size")}</TableHead>
                <TableHead className="sticky top-0 z-20 bg-background font-bold underline">{t("count.availableColumn")}</TableHead>
                <TableHead className="sticky top-0 z-20 bg-background font-bold underline">{t("count.toWashColumn")}</TableHead>
                <TableHead className="sticky top-0 right-0 z-30 bg-background text-right font-bold underline">
                  {t("columns.actions")}
                </TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {chosen.flatMap((article) =>
                article.sizes.map((size, index) => (
                  <TableRow key={size.article_size_id} className="group">
                    <TableCell className="font-medium">{index === 0 ? article.name : ""}</TableCell>
                    <TableCell>
                      {size.size_name} · {tFit(size.fit)}
                    </TableCell>
                    {(["available", "to_wash"] as const).map((status) => {
                      const booked = status === "available" ? size.available : size.to_wash;
                      const value = valueOf(size.article_size_id, status, booked);
                      const changed = value !== booked;
                      return (
                        <TableCell key={status}>
                          <div className="flex items-center gap-2">
                            <Input
                              type="number"
                              min={0}
                              step={1}
                              className={cn("w-24", changed && "border-amber-500")}
                              aria-label={t("count.countedFor", { size: `${article.name} ${size.size_name}`, status: t(`statuses.${status}`) })}
                              value={value}
                              onChange={(event) =>
                                setCounted((current) => ({
                                  ...current,
                                  [`${size.article_size_id}:${status}`]: Math.max(0, Number.parseInt(event.target.value, 10) || 0),
                                }))
                              }
                            />
                            {changed && (
                              <span className="text-xs text-amber-700 dark:text-amber-300">
                                {t("count.was", { count: booked })}
                              </span>
                            )}
                          </div>
                        </TableCell>
                      );
                    })}
                    <TableCell className="sticky right-0 z-10 bg-background group-hover:bg-muted/50">
                      {index === 0 && (
                        <div className="flex justify-end">
                          <Button
                            variant="ghost"
                            size="icon"
                            aria-label={t("removeArticle")}
                            title={t("removeArticle")}
                            onClick={() => setArticleIds((current) => current.filter((id) => id !== article.article_id))}
                          >
                            <X className="size-4" />
                          </Button>
                        </div>
                      )}
                    </TableCell>
                  </TableRow>
                )),
              )}
            </TableBody>
          </Table>
        </div>
      )}

      <div className="flex max-w-3xl flex-col gap-2">
        <Label htmlFor="atelier-count-note">{t("noteLabel")}</Label>
        <Textarea id="atelier-count-note" rows={2} value={note} onChange={(event) => setNote(event.target.value)} />
      </div>

      {canBook && (
        <div className="flex items-center gap-3">
          <Button onClick={handleBook} disabled={isBooking || differences.length === 0}>
            {t("count.book", { count: differences.length })}
          </Button>
        </div>
      )}
    </div>
  );
}
