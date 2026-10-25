"use client";

// One screen for Atelier's three simple stock bookings (block 3):
//   - "receipt"  Ontvangst: new pieces come in → available (reference + note);
//   - "wash"     Wassen: pieces to wash → available (opens with every article
//                that has pieces to wash, "Alles" fills in all of them);
//   - "writeoff" Afboeken: pieces leave the store from available or from to
//                wash, with a reason (damaged / lost / not returned / other).
// Pick articles, type a quantity per size, then Book. The quantities shown
// next to each size are the current stock in the relevant status.

import { useState } from "react";
import { Plus, X } from "lucide-react";
import { useTranslations } from "next-intl";
import { toast } from "sonner";
import { bookAtelierReceipt, bookAtelierWash, bookAtelierWriteOff, listAtelierStock } from "@/lib/api";
import type { AtelierStockArticle, AtelierStockSize } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { ArticleThumb } from "@/components/module-5/article-management";
import { ATELIER_STOCK_CHANGED_EVENT, atelierStockErrorMessage } from "@/components/module-5/atelier-stock-common";

type Mode = "receipt" | "wash" | "writeoff";
type Source = "available" | "to_wash";

const REASONS = ["damaged", "lost", "not_returned", "other"] as const;

interface StockBookingScreenProps {
  mode: Mode;
  initialStock: AtelierStockArticle[];
  canBook: boolean;
}

export function StockBookingScreen({ mode, initialStock, canBook }: StockBookingScreenProps) {
  const t = useTranslations("atelier.stock");
  const tFit = useTranslations("atelier.fits");
  const [stock, setStock] = useState(initialStock);
  // Afboeken takes from one status for the whole booking.
  const [source, setSource] = useState<Source>("available");
  // Wassen starts with every article that has pieces to wash.
  const [articleIds, setArticleIds] = useState<number[]>(() =>
    mode === "wash" ? initialStock.filter((article) => article.sizes.some((size) => size.to_wash > 0)).map((a) => a.article_id) : [],
  );
  const [quantities, setQuantities] = useState<Record<number, number>>({});
  const [reference, setReference] = useState("");
  const [note, setNote] = useState("");
  const [reason, setReason] = useState<(typeof REASONS)[number]>("damaged");
  const [isBooking, setIsBooking] = useState(false);

  // The pieces a size has in the status this booking takes from (receipts take from outside).
  function present(size: AtelierStockSize): number | null {
    if (mode === "receipt") return null;
    if (mode === "wash") return size.to_wash;
    return source === "available" ? size.available : size.to_wash;
  }

  // The sizes of an article that can be booked here.
  function bookableSizes(article: AtelierStockArticle): AtelierStockSize[] {
    if (mode === "receipt") return article.active ? article.sizes.filter((size) => size.active) : [];
    return article.sizes.filter((size) => (present(size) ?? 0) > 0);
  }

  const pickable = stock.filter((article) => !articleIds.includes(article.article_id) && bookableSizes(article).length > 0);
  const chosen = articleIds
    .map((id) => stock.find((article) => article.article_id === id))
    .filter((article): article is AtelierStockArticle => article !== undefined);

  const lines = Object.entries(quantities)
    .filter(([, quantity]) => quantity > 0)
    .map(([id, quantity]) => ({ article_size_id: Number(id), quantity }));
  const totalPieces = lines.reduce((sum, line) => sum + line.quantity, 0);

  function setQuantity(articleSizeId: number, value: string) {
    setQuantities((current) => ({ ...current, [articleSizeId]: Math.max(0, Number.parseInt(value, 10) || 0) }));
  }

  function removeArticle(article: AtelierStockArticle) {
    setArticleIds((current) => current.filter((id) => id !== article.article_id));
    setQuantities((current) => {
      const next = { ...current };
      for (const size of article.sizes) delete next[size.article_size_id];
      return next;
    });
  }

  // "Alles": fill in every piece present (washing everything, writing off everything).
  function fillAll(article: AtelierStockArticle) {
    setQuantities((current) => {
      const next = { ...current };
      for (const size of bookableSizes(article)) next[size.article_size_id] = present(size) ?? 0;
      return next;
    });
  }

  async function handleBook() {
    setIsBooking(true);
    try {
      const document =
        mode === "receipt"
          ? await bookAtelierReceipt({ lines, reference: reference.trim() || null, note: note.trim() || null })
          : mode === "wash"
            ? await bookAtelierWash({ lines, note: note.trim() || null })
            : await bookAtelierWriteOff({
                lines: lines.map((line) => ({ ...line, from_status: source })),
                reason,
                note: note.trim() || null,
              });
      toast.success(t("booked", { number: document.doc_number, count: document.total_quantity }));
      const fresh = await listAtelierStock();
      setStock(fresh);
      setQuantities({});
      setReference("");
      setNote("");
      // Wassen keeps the articles that still have pieces to wash; the others start empty.
      setArticleIds(
        mode === "wash" ? fresh.filter((article) => article.sizes.some((size) => size.to_wash > 0)).map((a) => a.article_id) : [],
      );
      window.dispatchEvent(new Event(ATELIER_STOCK_CHANGED_EVENT));
    } catch (error) {
      toast.error(atelierStockErrorMessage(t, error));
    } finally {
      setIsBooking(false);
    }
  }

  const noteRequired = mode === "writeoff" && reason === "other";

  return (
    <div className="flex flex-col gap-4">
      <div>
        <h1 className="text-2xl font-bold tracking-tight underline">{t(`${mode}.title`)}</h1>
        <p className="text-muted-foreground">{t(`${mode}.description`)}</p>
      </div>

      <div className="flex flex-wrap items-end gap-4">
        {mode === "writeoff" && (
          <div className="flex w-56 flex-col gap-2">
            <Label htmlFor="atelier-writeoff-source">{t("writeoff.sourceLabel")}</Label>
            <Select
              value={source}
              onValueChange={(value) => {
                if (!value) return;
                setSource(value as Source);
                setQuantities({});
              }}
            >
              <SelectTrigger id="atelier-writeoff-source">
                <SelectValue>{(value: string | null) => (value ? t(`statuses.${value}`) : "")}</SelectValue>
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="available">{t("statuses.available")}</SelectItem>
                <SelectItem value="to_wash">{t("statuses.to_wash")}</SelectItem>
              </SelectContent>
            </Select>
          </div>
        )}
        {/* Picking an article adds it with all its bookable sizes. */}
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
      </div>

      {chosen.length === 0 && <p className="text-sm text-muted-foreground">{t(`${mode}.empty`)}</p>}

      <div className="flex flex-col gap-3">
        {chosen.map((article) => (
          <Card key={article.article_id}>
            <CardContent className="flex flex-col gap-3">
              <div className="flex items-center gap-3">
                <ArticleThumb article={{ id: article.article_id, ...article }} />
                <div className="flex-1">
                  <p className="font-medium">{article.name}</p>
                  <p className="font-mono text-xs text-muted-foreground">{article.code}</p>
                </div>
                {mode !== "receipt" && (
                  <Button variant="outline" size="sm" onClick={() => fillAll(article)}>
                    {t("fillAll")}
                  </Button>
                )}
                <Button variant="ghost" size="icon" aria-label={t("removeArticle")} title={t("removeArticle")} onClick={() => removeArticle(article)}>
                  <X className="size-4" />
                </Button>
              </div>
              <div className="grid grid-cols-2 gap-3 sm:grid-cols-4 lg:grid-cols-6">
                {bookableSizes(article).map((size) => {
                  const inStock = present(size);
                  const quantity = quantities[size.article_size_id] ?? 0;
                  const tooMany = inStock !== null && quantity > inStock;
                  return (
                    <div key={size.article_size_id} className="flex flex-col gap-1">
                      <Label htmlFor={`atelier-qty-${size.article_size_id}`} className="text-sm">
                        {size.size_name} · {tFit(size.fit)}
                      </Label>
                      <Input
                        id={`atelier-qty-${size.article_size_id}`}
                        type="number"
                        min={0}
                        max={inStock ?? undefined}
                        step={1}
                        aria-invalid={tooMany}
                        value={quantity || ""}
                        placeholder="0"
                        onChange={(event) => setQuantity(size.article_size_id, event.target.value)}
                      />
                      <span className={tooMany ? "text-xs text-destructive" : "text-xs text-muted-foreground"}>
                        {inStock !== null ? t("present", { count: inStock }) : t("inStockAvailable", { count: size.available })}
                      </span>
                    </div>
                  );
                })}
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      <div className="grid max-w-3xl grid-cols-1 gap-4 sm:grid-cols-2">
        {mode === "receipt" && (
          <div className="flex flex-col gap-2">
            <Label htmlFor="atelier-booking-reference">{t("receipt.referenceLabel")}</Label>
            <Input id="atelier-booking-reference" value={reference} onChange={(event) => setReference(event.target.value)} />
          </div>
        )}
        {mode === "writeoff" && (
          <div className="flex flex-col gap-2">
            <Label htmlFor="atelier-writeoff-reason">{t("writeoff.reasonLabel")}</Label>
            <Select value={reason} onValueChange={(value) => value && setReason(value as (typeof REASONS)[number])}>
              <SelectTrigger id="atelier-writeoff-reason">
                <SelectValue>{(value: string | null) => (value ? t(`reasons.${value}`) : "")}</SelectValue>
              </SelectTrigger>
              <SelectContent>
                {REASONS.map((item) => (
                  <SelectItem key={item} value={item}>
                    {t(`reasons.${item}`)}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        )}
        <div className="flex flex-col gap-2 sm:col-span-2">
          <Label htmlFor="atelier-booking-note">
            {t("noteLabel")}
            {noteRequired && <span className="text-destructive"> *</span>}
          </Label>
          <Textarea id="atelier-booking-note" rows={2} value={note} onChange={(event) => setNote(event.target.value)} />
        </div>
      </div>

      {canBook && (
        <div className="flex items-center gap-3">
          <Button onClick={handleBook} disabled={isBooking || lines.length === 0 || (noteRequired && !note.trim())}>
            {t(`${mode}.book`, { count: totalPieces })}
          </Button>
        </div>
      )}
    </div>
  );
}
