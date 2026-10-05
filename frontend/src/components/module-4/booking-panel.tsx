"use client";

// StockMaster's booking panel: ONE screen for Inboeken, Kar laden,
// Uitboeken, Kar vertrekt, Kar terug and Kar uitladen, pre-set for the
// action of the page it's on (Telling has its own screen, count-panel.tsx).
// The person never chooses "from/to": the action decides it.
//
// It works like a basket: type a few letters of a product (the search shows
// its bin and stock), Enter, type the quantity, Enter — the line is added
// and the cursor is back in the search. Every line shows "before → after"
// for each place it touches, and a quantity above what's available is
// flagged in plain words. One "Bevestigen" (or Ctrl+Enter) books it all,
// under the logged-in user; the toast then offers "Ongedaan maken".
//
// Smart pre-filling:
// - Kar laden: the kar's missing needs (need − already in the kar);
// - Kar uitladen: "Alles uitladen";
// - Kar terug: what left with the kar, each line going back into the kar or
//   to free stock as the product is set up, so only differences are typed;
// - Inboeken from "Te bestellen": ?prefill=<product>:<qty>,...;
// - ?kar=<id> and ?product=<id> from the buttons on the other screens.

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { FileText, ListPlus, PackageOpen, Trash2 } from "lucide-react";
import { useLocale, useTranslations } from "next-intl";
import { useSearchParams } from "next/navigation";
import { toast } from "sonner";
import { Link } from "@/i18n/navigation";
import {
  createStockMasterBooking,
  getStockMasterKar,
  getStockMasterLookups,
  getStockMasterStock,
  listStockMasterKars,
  reverseStockMasterBooking,
  stockMasterBookingPdfUrl,
} from "@/lib/api";
import type {
  Season,
  StockMasterAction,
  StockMasterDocument,
  StockMasterKarDetail,
  StockMasterKarSummary,
  StockMasterLookups,
  StockMasterMyPermissions,
  StockMasterProductStock,
} from "@/lib/types";
import { cn } from "@/lib/utils";
import { Button, buttonVariants } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Textarea } from "@/components/ui/textarea";
import { KarSearch, ProductSearch, SelectedKar } from "@/components/module-4/stock-pickers";
import { StockMasterSeasonSelect, useStockMasterSeasonId } from "@/components/module-4/stockmaster-season-select";
import {
  STOCKMASTER_BASE,
  announceStockChanged,
  hasRight,
  stockErrorMessage,
} from "@/components/module-4/stockmaster-common";

interface BookingPanelProps {
  action: Exclude<StockMasterAction, "count">;
  seasons: Season[];
  permissions: StockMasterMyPermissions;
}

/** One line in the basket. */
interface BasketLine {
  productId: number;
  quantity: number;
  /** Only on "Kar terug": back into the kar or to free stock. */
  destination?: "kar" | "free";
  /** Only on "Kar terug": how many left with the kar. */
  dispatched?: number;
}

/** "Before → after" of one place a line touches. */
interface PlaceChange {
  label: string;
  before: number;
  after: number;
}

// Sentinel for "free stock" in the source dropdowns (Base UI needs a value).
const FREE_SOURCE = "free";
const NO_SELECTION = "none";

export function BookingPanel({ action, seasons, permissions }: BookingPanelProps) {
  const t = useTranslations("stockMaster");
  const tAction = useTranslations(`stockMaster.actions.${action}`);
  const locale = useLocale();
  const searchParams = useSearchParams();
  const seasonId = useStockMasterSeasonId(seasons);
  const season = seasons.find((item) => item.id === seasonId) ?? null;

  const isKarAction = action !== "book_in" && action !== "book_out";
  const usesBasket = action !== "kar_dispatch";

  // --- Data -----------------------------------------------------------------
  const [stock, setStock] = useState<StockMasterProductStock[]>([]);
  const [kars, setKars] = useState<StockMasterKarSummary[]>([]);
  const [lookups, setLookups] = useState<StockMasterLookups | null>(null);
  // The last loaded kar detail; only used while it belongs to the chosen kar.
  const [loadedKarDetail, setLoadedKarDetail] = useState<StockMasterKarDetail | null>(null);

  // --- Form -----------------------------------------------------------------
  // The kar the action is about (or, on Uitboeken, the kar taken out of).
  const [karId, setKarId] = useState<number | null>(() => Number(searchParams.get("kar")) || null);
  // Kar laden from another kar instead of free stock.
  const [fromKarId, setFromKarId] = useState<number | null>(() => Number(searchParams.get("from")) || null);
  const [lines, setLines] = useState<BasketLine[]>(() => parsePrefill(searchParams.get("prefill")));
  const [reference, setReference] = useState("");
  const [comment, setComment] = useState("");
  const [reasonId, setReasonId] = useState<number | null>(null);
  const [teamId, setTeamId] = useState<number | null>(null);
  const [festivalId, setFestivalId] = useState<number | null>(null);
  const [pendingProduct, setPendingProduct] = useState<StockMasterProductStock | null>(null);
  const [pendingQuantity, setPendingQuantity] = useState("1");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [lastBooking, setLastBooking] = useState<StockMasterDocument | null>(null);
  // The kar whose needs/contents were already put in the basket.
  const prefilledForKar = useRef<number | null>(null);

  const searchRef = useRef<HTMLInputElement>(null);
  const quantityRef = useRef<HTMLInputElement>(null);

  const productsById = useMemo(() => new Map(stock.map((product) => [product.product_id, product])), [stock]);
  const selectedKar = kars.find((kar) => kar.kar_id === karId) ?? null;
  const fromKar = kars.find((kar) => kar.kar_id === fromKarId) ?? null;
  const karDetail =
    isKarAction && loadedKarDetail !== null && loadedKarDetail.kar.kar_id === karId ? loadedKarDetail : null;
  const canUndo = hasRight(permissions, "bookings", "delete");
  const canSeeBookings = hasRight(permissions, "bookings", "view");
  const seasonLocked =
    season !== null && !season.periode_open && !permissions.editable_screen_keys.includes("stockmaster.closedseason");

  // A product passed in the URL (?product=) is made ready for its quantity
  // once, as soon as the products have arrived.
  const productParamUsed = useRef(false);

  // --- Loading --------------------------------------------------------------

  const reloadStock = useCallback(() => {
    getStockMasterStock()
      .then((products) => {
        setStock(products);
        const productParam = Number(searchParams.get("product")) || null;
        if (productParam !== null && !productParamUsed.current) {
          productParamUsed.current = true;
          const product = products.find((item) => item.product_id === productParam);
          if (product) {
            setPendingProduct(product);
            window.setTimeout(() => quantityRef.current?.select(), 50);
          }
        }
      })
      .catch(() => toast.error(t("errors.loadFailed")));
  }, [t, searchParams]);

  useEffect(() => {
    reloadStock();
    getStockMasterLookups()
      .then(setLookups)
      .catch(() => toast.error(t("errors.loadFailed")));
  }, [reloadStock, t]);

  const reloadKars = useCallback(() => {
    listStockMasterKars(seasonId)
      .then(setKars)
      .catch(() => toast.error(t("errors.loadFailed")));
  }, [seasonId, t]);

  useEffect(() => {
    reloadKars();
  }, [reloadKars]);

  /** Pre-fill the basket once per chosen kar: the missing needs on Kar
   *  laden (only while the basket is empty), what left with the kar on Kar
   *  terug, and the kar's team/festival on Kar vertrekt. */
  const prefillFor = useCallback(
    (detail: StockMasterKarDetail) => {
      if (prefilledForKar.current === detail.kar.kar_id) return;
      prefilledForKar.current = detail.kar.kar_id;
      if (action === "kar_load" && fromKarId === null) {
        setLines((current) =>
          current.length > 0
            ? current
            : detail.lines
                .filter((line) => line.missing > 0 && !line.is_blocked)
                .map((line) => ({ productId: line.product_id, quantity: line.missing })),
        );
      } else if (action === "kar_return") {
        setLines(
          detail.dispatched.map((line) => ({
            productId: line.product_id,
            quantity: line.quantity,
            dispatched: line.quantity,
            destination: line.stock_return_to,
          })),
        );
      } else if (action === "kar_dispatch") {
        setTeamId(detail.kar.team_id);
        setFestivalId(detail.festivals.length === 1 ? detail.festivals[0].id : null);
      }
    },
    [action, fromKarId],
  );

  const reloadKarDetail = useCallback(() => {
    if (karId === null || !isKarAction) return;
    getStockMasterKar(karId, seasonId)
      .then((detail) => {
        setLoadedKarDetail(detail);
        prefillFor(detail);
      })
      .catch(() => toast.error(t("errors.loadFailed")));
  }, [karId, seasonId, isKarAction, prefillFor, t]);

  useEffect(() => {
    reloadKarDetail();
  }, [reloadKarDetail]);

  // --- Availability and preview ---------------------------------------------

  /** How many pieces of a product are available at the line's source, or
   *  null when there's no limit (Inboeken, Kar terug). */
  function availableFor(product: StockMasterProductStock): number | null {
    const inKar = (id: number | null) => product.kars.find((kar) => kar.kar_id === id)?.quantity ?? 0;
    switch (action) {
      case "book_out":
        return karId !== null ? inKar(karId) : product.free;
      case "kar_load":
        return fromKarId !== null ? inKar(fromKarId) : product.free;
      case "kar_unload":
        return inKar(karId);
      default:
        return null;
    }
  }

  /** The places a line touches, with their quantity before and after. */
  function placeChanges(line: BasketLine, product: StockMasterProductStock): PlaceChange[] {
    const inKar = (id: number | null) => product.kars.find((kar) => kar.kar_id === id)?.quantity ?? 0;
    const free = { label: t("common.freeStock"), before: product.free };
    const kar = (id: number | null, nummer: string | undefined) => ({
      label: nummer ?? "?",
      before: inKar(id),
    });
    const quantity = line.quantity;
    switch (action) {
      case "book_in":
        return [{ ...free, after: free.before + quantity }];
      case "book_out": {
        const source = karId !== null ? kar(karId, selectedKar?.kar_nummer) : free;
        return [{ ...source, after: source.before - quantity }];
      }
      case "kar_load": {
        const source = fromKarId !== null ? kar(fromKarId, fromKar?.kar_nummer) : free;
        const target = kar(karId, selectedKar?.kar_nummer);
        return [
          { ...source, after: source.before - quantity },
          { ...target, after: target.before + quantity },
        ];
      }
      case "kar_unload": {
        const source = kar(karId, selectedKar?.kar_nummer);
        return [
          { ...source, after: source.before - quantity },
          { ...free, after: free.before + quantity },
        ];
      }
      case "kar_return": {
        if (quantity === 0) return [];
        const target = line.destination === "free" ? free : kar(karId, selectedKar?.kar_nummer);
        return [{ ...target, after: target.before + quantity }];
      }
      default:
        return [];
    }
  }

  /** A friendly problem with one line, or null when it's fine. */
  function lineProblem(line: BasketLine, product: StockMasterProductStock): string | null {
    if (action !== "kar_return" && line.quantity < 1) return t("booking.quantityTooLow");
    const available = availableFor(product);
    if (available !== null && line.quantity > available) {
      const place =
        action === "kar_unload" || (action === "book_out" && karId !== null)
          ? selectedKar?.kar_nummer
          : action === "kar_load" && fromKarId !== null
            ? fromKar?.kar_nummer
            : t("common.freeStock");
      return t("booking.notEnough", { count: available, place: place ?? "" });
    }
    if ((action === "book_in" || action === "kar_load") && product.is_blocked) return t("booking.blocked");
    return null;
  }

  // --- Basket actions -------------------------------------------------------

  function choosePendingProduct(product: StockMasterProductStock) {
    setPendingProduct(product);
    // On Kar laden, suggest what the kar still misses.
    const missing = karDetail?.lines.find((line) => line.product_id === product.product_id)?.missing;
    setPendingQuantity(String(action === "kar_load" && missing ? missing : 1));
    window.setTimeout(() => quantityRef.current?.select(), 0);
  }

  function addPendingLine() {
    if (!pendingProduct) return;
    const quantity = Number.parseInt(pendingQuantity, 10);
    if (!Number.isFinite(quantity) || quantity < (action === "kar_return" ? 0 : 1)) {
      toast.error(t("booking.quantityTooLow"));
      return;
    }
    setLines((current) => {
      const existing = current.find((line) => line.productId === pendingProduct.product_id);
      if (existing) {
        return current.map((line) =>
          line === existing ? { ...line, quantity: line.quantity + quantity } : line,
        );
      }
      return [
        ...current,
        {
          productId: pendingProduct.product_id,
          quantity,
          ...(action === "kar_return" ? { destination: pendingProduct.stock_return_to, dispatched: 0 } : {}),
        },
      ];
    });
    setPendingProduct(null);
    setPendingQuantity("1");
    window.setTimeout(() => searchRef.current?.focus(), 0);
  }

  function updateLine(productId: number, changes: Partial<BasketLine>) {
    setLines((current) => current.map((line) => (line.productId === productId ? { ...line, ...changes } : line)));
  }

  function removeLine(productId: number) {
    setLines((current) => current.filter((line) => line.productId !== productId));
  }

  function fillMissing() {
    if (!karDetail) return;
    setLines(
      karDetail.lines
        .filter((line) => line.missing > 0 && !line.is_blocked)
        .map((line) => ({ productId: line.product_id, quantity: line.missing })),
    );
  }

  function fillEverything() {
    if (!karDetail) return;
    setLines(
      karDetail.lines
        .filter((line) => line.in_kar > 0)
        .map((line) => ({ productId: line.product_id, quantity: line.in_kar })),
    );
  }

  function chooseKar(kar: StockMasterKarSummary | null) {
    setKarId(kar?.kar_id ?? null);
    prefilledForKar.current = null;
    // Return lines belong to one kar; other baskets stay.
    if (action === "kar_return" || action === "kar_unload") setLines([]);
  }

  // --- Booking --------------------------------------------------------------

  const reasons = (lookups?.reasons ?? []).filter(
    (reason) => reason.applies_to === null || reason.applies_to === action,
  );
  const activeLines = action === "kar_return" ? lines : lines.filter((line) => line.quantity > 0);
  const problems = activeLines.some((line) => {
    const product = productsById.get(line.productId);
    return !product || lineProblem(line, product) !== null;
  });
  const missingKar = isKarAction && karId === null;
  const missingReason = action === "book_out" && reasonId === null;
  const emptyBasket = usesBasket && action !== "kar_return" && activeLines.length === 0;
  const canSubmit =
    seasonId !== null && !seasonLocked && !missingKar && !missingReason && !emptyBasket && !problems && !isSubmitting;

  async function handleSubmit() {
    if (!canSubmit || seasonId === null) return;
    setIsSubmitting(true);
    try {
      const document = await createStockMasterBooking({
        action,
        season_id: seasonId,
        kar_id: action === "book_in" ? null : karId,
        from_kar_id: action === "kar_load" ? fromKarId : null,
        team_id: action === "kar_dispatch" ? teamId : null,
        festival_id: action === "kar_dispatch" ? festivalId : null,
        reference: reference.trim() || null,
        reason_id: reasonId,
        comment: comment.trim() || null,
        lines: usesBasket
          ? activeLines
              .filter((line) => action !== "kar_return" || line.quantity > 0)
              .map((line) => ({ product_id: line.productId, quantity: line.quantity, destination: line.destination }))
          : [],
      });
      setLastBooking(document);
      toast.success(t("booking.booked", { number: document.doc_number }), {
        action: canUndo ? { label: t("booking.undo"), onClick: () => void undo(document) } : undefined,
      });
      // Start the next booking with a clean basket.
      setLines([]);
      setReference("");
      setComment("");
      setReasonId(null);
      prefilledForKar.current = karId;
      if (action === "kar_dispatch" || action === "kar_return") setKarId(null);
      reloadStock();
      reloadKars();
      reloadKarDetail();
      announceStockChanged();
      window.setTimeout(() => searchRef.current?.focus(), 0);
    } catch (error) {
      toast.error(stockErrorMessage(t, error));
    } finally {
      setIsSubmitting(false);
    }
  }

  async function undo(document: StockMasterDocument) {
    try {
      const reversal = await reverseStockMasterBooking(document.id);
      toast.success(t("booking.undone", { number: document.doc_number }));
      setLastBooking(reversal);
      reloadStock();
      reloadKars();
      reloadKarDetail();
      announceStockChanged();
    } catch (error) {
      toast.error(stockErrorMessage(t, error));
    }
  }

  // Ctrl+Enter anywhere in the panel books.
  function handleKeyDown(event: React.KeyboardEvent) {
    if (event.key === "Enter" && (event.ctrlKey || event.metaKey)) {
      event.preventDefault();
      void handleSubmit();
    }
  }

  // --- Rendering --------------------------------------------------------------

  // Which kars can be picked for this action.
  const karDisabled = (kar: StockMasterKarSummary) => (action === "kar_return" ? !kar.is_out : kar.is_out);

  return (
    <div className="flex flex-col gap-6" onKeyDown={handleKeyDown}>
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight underline">{tAction("title")}</h1>
          <p className="text-muted-foreground">{tAction("description")}</p>
        </div>
        <StockMasterSeasonSelect seasons={seasons} seasonId={seasonId} />
      </div>

      {seasonLocked && <p className="rounded-md bg-destructive/10 px-3 py-2 text-sm text-destructive">{t("errors.season_closed")}</p>}

      <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_20rem]">
        <div className="flex flex-col gap-6">
          {/* The kar (kar actions), or the source (Uitboeken). */}
          {isKarAction && (
            <div className="flex flex-col gap-2">
              <Label htmlFor="booking-kar">{t("booking.karLabel")}</Label>
              {selectedKar ? (
                <SelectedKar kar={selectedKar} onClear={() => chooseKar(null)} />
              ) : (
                <KarSearch id="booking-kar" kars={kars} onSelect={chooseKar} isDisabled={karDisabled} autoFocus />
              )}
              {selectedKar && karDisabled(selectedKar) && (
                <p className="text-sm text-destructive">
                  {action === "kar_return"
                    ? t("errors.kar_not_out", { p1: selectedKar.kar_nummer })
                    : t("errors.kar_out", { p1: selectedKar.kar_nummer })}
                </p>
              )}
            </div>
          )}

          {action === "kar_load" && (
            <SourceSelect
              id="booking-from"
              label={t("booking.fromLabel")}
              value={fromKarId}
              kars={kars.filter((kar) => !kar.is_out && kar.kar_id !== karId && kar.total_quantity > 0)}
              onChange={(value) => {
                setFromKarId(value);
                setLines([]);
              }}
            />
          )}
          {action === "book_out" && (
            <SourceSelect
              id="booking-source"
              label={t("booking.fromLabel")}
              value={karId}
              kars={kars.filter((kar) => !kar.is_out && kar.total_quantity > 0)}
              onChange={(value) => {
                setKarId(value);
                setLines([]);
              }}
            />
          )}

          {action === "kar_dispatch" && karDetail && selectedKar && (
            <DispatchContents detail={karDetail} />
          )}

          {usesBasket && (!isKarAction || selectedKar) && (
            <Card>
              <CardContent className="flex flex-col gap-4">
                <div className="flex flex-wrap items-end gap-3">
                  <div className="flex min-w-64 flex-1 flex-col gap-2">
                    <Label htmlFor="booking-product">{t("booking.productLabel")}</Label>
                    {pendingProduct ? (
                      <div className="flex h-8 items-center gap-2 rounded-md border bg-muted/40 px-3 text-sm">
                        <span className="font-medium">{pendingProduct.name}</span>
                        <span className="text-muted-foreground">{pendingProduct.bin_label}</span>
                        <button
                          type="button"
                          className="ml-auto text-xs text-muted-foreground underline"
                          onClick={() => {
                            setPendingProduct(null);
                            window.setTimeout(() => searchRef.current?.focus(), 0);
                          }}
                        >
                          {t("booking.otherProduct")}
                        </button>
                      </div>
                    ) : (
                      <ProductSearch
                        id="booking-product"
                        ref={searchRef}
                        products={stock}
                        onSelect={choosePendingProduct}
                        blockBlocked={action === "book_in" || action === "kar_load"}
                        karId={action === "kar_load" ? (fromKarId ?? karId) : karId}
                        autoFocus={!isKarAction}
                      />
                    )}
                  </div>
                  <div className="flex w-28 flex-col gap-2">
                    <Label htmlFor="booking-quantity">{t("booking.quantityLabel")}</Label>
                    <Input
                      id="booking-quantity"
                      ref={quantityRef}
                      type="number"
                      min={action === "kar_return" ? 0 : 1}
                      step={1}
                      inputMode="numeric"
                      value={pendingQuantity}
                      disabled={!pendingProduct}
                      onChange={(event) => setPendingQuantity(event.target.value)}
                      onKeyDown={(event) => {
                        if (event.key === "Enter" && !event.ctrlKey && !event.metaKey) {
                          event.preventDefault();
                          addPendingLine();
                        }
                      }}
                    />
                  </div>
                  <Button variant="outline" onClick={addPendingLine} disabled={!pendingProduct}>
                    <ListPlus />
                    {t("booking.addLine")}
                  </Button>
                  {action === "kar_load" && fromKarId === null && karDetail && (
                    <Button variant="outline" onClick={fillMissing}>
                      {t("booking.fillMissing")}
                    </Button>
                  )}
                  {action === "kar_unload" && karDetail && (
                    <Button variant="outline" onClick={fillEverything}>
                      <PackageOpen />
                      {t("booking.unloadEverything")}
                    </Button>
                  )}
                </div>
                <p className="text-xs text-muted-foreground">{t("booking.keyboardHint")}</p>

                <BasketTable
                  action={action}
                  lines={lines}
                  productsById={productsById}
                  placeChanges={placeChanges}
                  lineProblem={lineProblem}
                  onChange={updateLine}
                  onRemove={removeLine}
                />
              </CardContent>
            </Card>
          )}
        </div>

        {/* Side column: the booking's details and the confirm button. */}
        <div className="flex flex-col gap-4">
          <Card>
            <CardContent className="flex flex-col gap-4">
              {action === "kar_dispatch" && (
                <>
                  <NamedSelect
                    id="booking-team"
                    label={t("booking.teamLabel")}
                    value={teamId}
                    items={lookups?.teams ?? []}
                    emptyLabel={t("booking.noTeam")}
                    onChange={setTeamId}
                  />
                  <NamedSelect
                    id="booking-festival"
                    label={t("booking.festivalLabel")}
                    value={festivalId}
                    items={karDetail?.festivals ?? []}
                    emptyLabel={t("booking.noFestival")}
                    onChange={setFestivalId}
                  />
                </>
              )}
              {action === "book_out" && (
                <NamedSelect
                  id="booking-reason"
                  label={`${t("booking.reasonLabel")} *`}
                  value={reasonId}
                  items={reasons}
                  emptyLabel={t("booking.chooseReason")}
                  onChange={setReasonId}
                />
              )}
              {(action === "book_in" || action === "book_out" || action === "kar_load" || action === "kar_dispatch") && (
                <div className="flex flex-col gap-2">
                  <Label htmlFor="booking-reference">
                    {action === "book_in" ? t("booking.deliveryNoteLabel") : t("booking.referenceLabel")}
                  </Label>
                  <Input id="booking-reference" value={reference} onChange={(event) => setReference(event.target.value)} />
                </div>
              )}
              <div className="flex flex-col gap-2">
                <Label htmlFor="booking-comment">{t("booking.commentLabel")}</Label>
                <Textarea id="booking-comment" value={comment} onChange={(event) => setComment(event.target.value)} rows={2} />
              </div>

              <BookingSummary action={action} lines={activeLines} detail={karDetail} />

              <Button size="lg" onClick={() => void handleSubmit()} disabled={!canSubmit}>
                {tAction("confirm")}
              </Button>
              {missingReason && <p className="text-xs text-muted-foreground">{t("errors.reason_required")}</p>}
              <p className="text-xs text-muted-foreground">{t("booking.confirmHint")}</p>
            </CardContent>
          </Card>

          {lastBooking && (
            <Card>
              <CardContent className="flex flex-col gap-2 text-sm">
                <span className="font-semibold">{t("booking.lastBooking")}</span>
                <span>
                  {lastBooking.doc_number} · {t(`docTypes.${lastBooking.doc_type}`)} ·{" "}
                  {t("booking.pieces", { count: lastBooking.total_quantity })}
                </span>
                <div className="flex flex-wrap gap-2">
                  {(canSeeBookings || lastBooking.doc_type === "kar_dispatch") && (
                    <a
                      href={stockMasterBookingPdfUrl(lastBooking.id, locale)}
                      target="_blank"
                      rel="noreferrer"
                      className={buttonVariants({ variant: "outline", size: "sm" })}
                    >
                      <FileText />
                      {lastBooking.doc_type === "kar_dispatch" ? t("booking.dispatchNote") : t("booking.bookingNote")}
                    </a>
                  )}
                  {canSeeBookings && (
                    <Link
                      href={`${STOCKMASTER_BASE}/bookings/${lastBooking.id}`}
                      className={buttonVariants({ variant: "outline", size: "sm" })}
                    >
                      {t("booking.viewBooking")}
                    </Link>
                  )}
                  {canUndo && lastBooking.doc_type !== "reversal" && lastBooking.status === "posted" && (
                    <Button variant="ghost" size="sm" onClick={() => void undo(lastBooking)}>
                      {t("booking.undo")}
                    </Button>
                  )}
                </div>
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}

/** "?prefill=12:5,13:2" (from Te bestellen) as basket lines. */
function parsePrefill(value: string | null): BasketLine[] {
  if (!value) return [];
  return value
    .split(",")
    .map((part) => part.split(":").map(Number))
    .filter(([productId, quantity]) => productId > 0 && quantity > 0)
    .map(([productId, quantity]) => ({ productId, quantity }));
}

interface SourceSelectProps {
  id: string;
  label: string;
  value: number | null;
  kars: StockMasterKarSummary[];
  onChange: (karId: number | null) => void;
}

/** "Van": free stock (default) or a kar standing in the warehouse. */
function SourceSelect({ id, label, value, kars, onChange }: SourceSelectProps) {
  const t = useTranslations("stockMaster");
  return (
    <div className="flex max-w-sm flex-col gap-2">
      <Label htmlFor={id}>{label}</Label>
      <Select
        value={value === null ? FREE_SOURCE : String(value)}
        onValueChange={(next) => onChange(next && next !== FREE_SOURCE ? Number(next) : null)}
      >
        <SelectTrigger id={id}>
          <SelectValue>
            {(current: string | null) =>
              current === FREE_SOURCE || !current
                ? t("common.freeStock")
                : t("booking.fromKar", { kar: kars.find((kar) => String(kar.kar_id) === current)?.kar_nummer ?? "" })
            }
          </SelectValue>
        </SelectTrigger>
        <SelectContent>
          <SelectItem value={FREE_SOURCE}>{t("common.freeStock")}</SelectItem>
          {kars.map((kar) => (
            <SelectItem key={kar.kar_id} value={String(kar.kar_id)}>
              {t("booking.fromKar", { kar: kar.kar_nummer })}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  );
}

interface NamedSelectProps {
  id: string;
  label: string;
  value: number | null;
  items: { id: number; name: string }[];
  emptyLabel: string;
  onChange: (value: number | null) => void;
}

/** A dropdown of {id, name} items with an "empty" choice. */
export function NamedSelect({ id, label, value, items, emptyLabel, onChange }: NamedSelectProps) {
  return (
    <div className="flex flex-col gap-2">
      <Label htmlFor={id}>{label}</Label>
      <Select
        value={value === null ? NO_SELECTION : String(value)}
        onValueChange={(next) => onChange(next && next !== NO_SELECTION ? Number(next) : null)}
      >
        <SelectTrigger id={id} className="w-full">
          <SelectValue>
            {(current: string | null) => items.find((item) => String(item.id) === current)?.name ?? emptyLabel}
          </SelectValue>
        </SelectTrigger>
        <SelectContent>
          <SelectItem value={NO_SELECTION}>{emptyLabel}</SelectItem>
          {items.map((item) => (
            <SelectItem key={item.id} value={String(item.id)}>
              {item.name}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  );
}

interface BasketTableProps {
  action: StockMasterAction;
  lines: BasketLine[];
  productsById: Map<number, StockMasterProductStock>;
  placeChanges: (line: BasketLine, product: StockMasterProductStock) => PlaceChange[];
  lineProblem: (line: BasketLine, product: StockMasterProductStock) => string | null;
  onChange: (productId: number, changes: Partial<BasketLine>) => void;
  onRemove: (productId: number) => void;
}

/** The basket: one row per product, with before → after and any problem. */
function BasketTable({ action, lines, productsById, placeChanges, lineProblem, onChange, onRemove }: BasketTableProps) {
  const t = useTranslations("stockMaster");
  const isReturn = action === "kar_return";

  if (lines.length === 0) {
    return <p className="rounded-md border border-dashed px-4 py-6 text-center text-sm text-muted-foreground">{t("booking.emptyBasket")}</p>;
  }

  return (
    <div className="rounded-md border [&>div]:max-h-[55vh] [&>div]:overflow-y-auto">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead className="sticky top-0 z-20 bg-background font-bold underline">{t("booking.productLabel")}</TableHead>
            {isReturn && (
              <TableHead className="sticky top-0 z-20 bg-background text-right font-bold underline">{t("booking.dispatched")}</TableHead>
            )}
            <TableHead className="sticky top-0 z-20 w-28 bg-background font-bold underline">
              {isReturn ? t("booking.returned") : t("booking.quantityLabel")}
            </TableHead>
            {isReturn && (
              <TableHead className="sticky top-0 z-20 bg-background font-bold underline">{t("booking.destination")}</TableHead>
            )}
            <TableHead className="sticky top-0 z-20 bg-background font-bold underline">{t("booking.preview")}</TableHead>
            <TableHead className="sticky top-0 right-0 z-30 w-12 bg-background text-right font-bold underline">
              <span className="sr-only">{t("common.actions")}</span>
            </TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {lines.map((line) => {
            const product = productsById.get(line.productId);
            if (!product) return null;
            const problem = lineProblem(line, product);
            const notReturned = isReturn ? (line.dispatched ?? 0) - line.quantity : 0;
            return (
              <TableRow key={line.productId} className="group">
                <TableCell>
                  <div className="font-medium">{product.name}</div>
                  <div className="text-xs text-muted-foreground">{product.bin_label ?? t("common.noBin")}</div>
                  {problem && <div className="text-xs font-medium text-destructive">{problem}</div>}
                  {isReturn && notReturned > 0 && (
                    <div className="text-xs text-orange-700 dark:text-orange-300">
                      {product.is_consumable
                        ? t("booking.consumed", { count: notReturned })
                        : t("booking.missing", { count: notReturned })}
                    </div>
                  )}
                </TableCell>
                {isReturn && <TableCell className="text-right tabular-nums">{line.dispatched ?? 0}</TableCell>}
                <TableCell>
                  <Input
                    type="number"
                    min={isReturn ? 0 : 1}
                    step={1}
                    inputMode="numeric"
                    aria-label={t("booking.quantityLabel")}
                    className={cn("w-24", problem && "border-destructive")}
                    value={line.quantity}
                    onChange={(event) =>
                      onChange(line.productId, { quantity: Math.max(0, Number.parseInt(event.target.value, 10) || 0) })
                    }
                  />
                </TableCell>
                {isReturn && (
                  <TableCell>
                    <Select
                      value={line.destination ?? "kar"}
                      onValueChange={(value) => onChange(line.productId, { destination: value === "free" ? "free" : "kar" })}
                    >
                      <SelectTrigger className="w-40" aria-label={t("booking.destination")}>
                        <SelectValue>
                          {(value: string | null) => (value === "free" ? t("common.freeStock") : t("booking.backInKar"))}
                        </SelectValue>
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="kar">{t("booking.backInKar")}</SelectItem>
                        <SelectItem value="free">{t("common.freeStock")}</SelectItem>
                      </SelectContent>
                    </Select>
                  </TableCell>
                )}
                <TableCell className="text-sm tabular-nums">
                  {placeChanges(line, product).map((change) => (
                    <div key={change.label} className={cn(change.after < 0 && "text-destructive")}>
                      <span className="text-muted-foreground">{change.label}</span> {change.before} → <strong>{change.after}</strong>
                    </div>
                  ))}
                </TableCell>
                <TableCell className="sticky right-0 z-10 bg-background text-right group-hover:bg-muted/50">
                  <Button variant="ghost" size="icon-sm" onClick={() => onRemove(line.productId)} aria-label={t("booking.removeLine")}>
                    <Trash2 />
                  </Button>
                </TableCell>
              </TableRow>
            );
          })}
        </TableBody>
      </Table>
    </div>
  );
}

/** What leaves with the kar on "Kar vertrekt" (read-only). */
function DispatchContents({ detail }: { detail: StockMasterKarDetail }) {
  const t = useTranslations("stockMaster");
  const contents = detail.lines.filter((line) => line.in_kar > 0);
  const missing = detail.lines.filter((line) => line.missing > 0);
  return (
    <Card>
      <CardContent className="flex flex-col gap-3">
        <h2 className="font-semibold">{t("booking.leavesWithKar")}</h2>
        {contents.length === 0 ? (
          <p className="text-sm text-muted-foreground">{t("booking.karEmpty")}</p>
        ) : (
          <ul className="divide-y text-sm">
            {contents.map((line) => (
              <li key={line.product_id} className="flex justify-between py-1.5">
                <span>{line.name}</span>
                <span className="font-semibold tabular-nums">{line.in_kar}</span>
              </li>
            ))}
          </ul>
        )}
        {missing.length > 0 && (
          <p className="rounded-md bg-orange-50 px-3 py-2 text-sm text-orange-800 dark:bg-orange-500/10 dark:text-orange-200">
            {t("booking.stillMissing", { count: missing.reduce((sum, line) => sum + line.missing, 0) })}
          </p>
        )}
      </CardContent>
    </Card>
  );
}

/** "3 producten · 12 stuks" above the confirm button. */
function BookingSummary({
  action,
  lines,
  detail,
}: {
  action: StockMasterAction;
  lines: BasketLine[];
  detail: StockMasterKarDetail | null;
}) {
  const t = useTranslations("stockMaster.booking");
  if (action === "kar_dispatch") {
    const contents = detail?.lines.filter((line) => line.in_kar > 0) ?? [];
    return (
      <p className="text-sm">
        {t("summary", { products: contents.length, pieces: contents.reduce((sum, line) => sum + line.in_kar, 0) })}
      </p>
    );
  }
  const counted = lines.filter((line) => line.quantity > 0);
  return (
    <p className="text-sm">
      {t("summary", { products: counted.length, pieces: counted.reduce((sum, line) => sum + line.quantity, 0) })}
    </p>
  );
}
