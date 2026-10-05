"use client";

// StockMaster's "Telling" (stock count). Choose what to count — the free
// stock of a warehouse (optionally a bin range, e.g. "A" to "B") or one
// kar — and the list comes pre-filled with the expected quantities, sorted
// by bin. Only the lines that differ need typing; the differences are
// booked in one go (under the logged-in user), the rest is left alone.
// The printable Telblad has the same list with an empty "geteld" column.

import { useEffect, useMemo, useState } from "react";
import { FileText } from "lucide-react";
import { useLocale, useTranslations } from "next-intl";
import { useSearchParams } from "next/navigation";
import { toast } from "sonner";
import {
  createStockMasterBooking,
  getStockMasterCountSheet,
  getStockMasterLookups,
  getStockMasterStock,
  listStockMasterKars,
  stockMasterCountSheetPdfUrl,
  type StockMasterCountScope,
} from "@/lib/api";
import type {
  Season,
  StockMasterCountSheetLine,
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
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Textarea } from "@/components/ui/textarea";
import { NamedSelect } from "@/components/module-4/booking-panel";
import { KarSearch, ProductSearch, SelectedKar } from "@/components/module-4/stock-pickers";
import { StockMasterSeasonSelect, useStockMasterSeasonId } from "@/components/module-4/stockmaster-season-select";
import { announceStockChanged, hasRight, stockErrorMessage } from "@/components/module-4/stockmaster-common";

interface CountPanelProps {
  seasons: Season[];
  permissions: StockMasterMyPermissions;
}

/** One line being counted. */
interface CountRow extends StockMasterCountSheetLine {
  counted: string;
}

export function CountPanel({ seasons, permissions }: CountPanelProps) {
  const t = useTranslations("stockMaster");
  const tCount = useTranslations("stockMaster.count");
  const locale = useLocale();
  const searchParams = useSearchParams();
  const seasonId = useStockMasterSeasonId(seasons);
  const season = seasons.find((item) => item.id === seasonId) ?? null;
  const canCount = hasRight(permissions, "count", "create");
  const seasonLocked =
    season !== null && !season.periode_open && !permissions.editable_screen_keys.includes("stockmaster.closedseason");

  const [lookups, setLookups] = useState<StockMasterLookups | null>(null);
  const [kars, setKars] = useState<StockMasterKarSummary[]>([]);
  const [stock, setStock] = useState<StockMasterProductStock[]>([]);

  // What to count: a kar, or a warehouse (+ bin range).
  const [mode, setMode] = useState<"free" | "kar">(() => (searchParams.get("kar") ? "kar" : "free"));
  const [karId, setKarId] = useState<number | null>(() => Number(searchParams.get("kar")) || null);
  const [warehouseId, setWarehouseId] = useState<number | null>(null);
  const [binFrom, setBinFrom] = useState("");
  const [binTo, setBinTo] = useState("");

  const [rows, setRows] = useState<CountRow[] | null>(null);
  const [reasonId, setReasonId] = useState<number | null>(null);
  const [comment, setComment] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    getStockMasterLookups()
      .then((result) => {
        setLookups(result);
        // "Telverschil" (or the first count reason) is the natural default.
        const countReason = result.reasons.find((reason) => reason.applies_to === "count");
        if (countReason) setReasonId(countReason.id);
      })
      .catch(() => toast.error(t("errors.loadFailed")));
    getStockMasterStock()
      .then(setStock)
      .catch(() => toast.error(t("errors.loadFailed")));
  }, [t]);

  useEffect(() => {
    listStockMasterKars(seasonId)
      .then(setKars)
      .catch(() => toast.error(t("errors.loadFailed")));
  }, [seasonId, t]);

  const scope: StockMasterCountScope = useMemo(
    () =>
      mode === "kar"
        ? { kar_id: karId }
        : { warehouse_id: warehouseId, bin_from: binFrom.trim() || null, bin_to: binTo.trim() || null },
    [mode, karId, warehouseId, binFrom, binTo],
  );
  const scopeReady = mode === "free" || karId !== null;

  function loadSheet() {
    if (!scopeReady) return;
    getStockMasterCountSheet(scope)
      .then((lines) => setRows(lines.map((line) => ({ ...line, counted: String(line.expected) }))))
      .catch((error) => toast.error(stockErrorMessage(t, error)));
  }

  // Starting on a kar (?kar=) loads its list right away.
  useEffect(() => {
    if (mode === "kar" && karId !== null && rows === null) loadSheet();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [karId]);

  function addProduct(product: StockMasterProductStock) {
    if (rows?.some((row) => row.product_id === product.product_id)) return;
    const expected =
      mode === "kar" ? (product.kars.find((kar) => kar.kar_id === karId)?.quantity ?? 0) : product.free;
    setRows((current) => [
      ...(current ?? []),
      {
        product_id: product.product_id,
        name: product.name,
        bin_label: product.bin_label,
        warehouse_location: product.warehouse_location,
        expected,
        counted: String(expected),
      },
    ]);
  }

  const differences = (rows ?? []).filter((row) => row.counted !== "" && Number(row.counted) !== row.expected);
  const invalid = (rows ?? []).some((row) => row.counted === "" || Number(row.counted) < 0 || !Number.isInteger(Number(row.counted)));

  async function handleSubmit() {
    if (seasonId === null || differences.length === 0 || invalid || seasonLocked) return;
    setIsSubmitting(true);
    try {
      const document = await createStockMasterBooking({
        action: "count",
        season_id: seasonId,
        kar_id: mode === "kar" ? karId : null,
        reason_id: reasonId,
        comment: comment.trim() || null,
        // Only the lines that differ; the backend checks against the
        // latest stock and books exactly the difference.
        lines: differences.map((row) => ({ product_id: row.product_id, quantity: Number(row.counted) })),
      });
      toast.success(t("booking.booked", { number: document.doc_number }));
      announceStockChanged();
      setComment("");
      loadSheet();
    } catch (error) {
      toast.error(stockErrorMessage(t, error));
    } finally {
      setIsSubmitting(false);
    }
  }

  const countReasons = (lookups?.reasons ?? []).filter(
    (reason) => reason.applies_to === null || reason.applies_to === "count",
  );
  const selectedKar = kars.find((kar) => kar.kar_id === karId) ?? null;

  return (
    <div
      className="flex flex-col gap-6"
      onKeyDown={(event) => {
        if (event.key === "Enter" && (event.ctrlKey || event.metaKey)) {
          event.preventDefault();
          void handleSubmit();
        }
      }}
    >
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight underline">{t("actions.count.title")}</h1>
          <p className="text-muted-foreground">{t("actions.count.description")}</p>
        </div>
        <StockMasterSeasonSelect seasons={seasons} seasonId={seasonId} />
      </div>

      {seasonLocked && <p className="rounded-md bg-destructive/10 px-3 py-2 text-sm text-destructive">{t("errors.season_closed")}</p>}

      <Card>
        <CardContent className="flex flex-col gap-4">
          <div className="flex gap-2">
            <Button variant={mode === "free" ? "default" : "outline"} onClick={() => { setMode("free"); setRows(null); }}>
              {tCount("modeFree")}
            </Button>
            <Button variant={mode === "kar" ? "default" : "outline"} onClick={() => { setMode("kar"); setRows(null); }}>
              {tCount("modeKar")}
            </Button>
          </div>

          {mode === "free" ? (
            <div className="flex flex-wrap items-end gap-3">
              <div className="w-56">
                <NamedSelect
                  id="count-warehouse"
                  label={tCount("warehouseLabel")}
                  value={warehouseId}
                  items={lookups?.warehouses ?? []}
                  emptyLabel={tCount("allWarehouses")}
                  onChange={setWarehouseId}
                />
              </div>
              <div className="flex w-32 flex-col gap-2">
                <Label htmlFor="count-bin-from">{tCount("binFrom")}</Label>
                <Input id="count-bin-from" value={binFrom} onChange={(event) => setBinFrom(event.target.value)} placeholder="A" />
              </div>
              <div className="flex w-32 flex-col gap-2">
                <Label htmlFor="count-bin-to">{tCount("binTo")}</Label>
                <Input id="count-bin-to" value={binTo} onChange={(event) => setBinTo(event.target.value)} placeholder="C" />
              </div>
            </div>
          ) : (
            <div className="flex max-w-md flex-col gap-2">
              <Label htmlFor="count-kar">{t("booking.karLabel")}</Label>
              {selectedKar ? (
                <SelectedKar kar={selectedKar} onClear={() => { setKarId(null); setRows(null); }} />
              ) : (
                <KarSearch
                  id="count-kar"
                  kars={kars}
                  isDisabled={(kar) => kar.is_out}
                  onSelect={(kar) => { setKarId(kar.kar_id); setRows(null); }}
                />
              )}
            </div>
          )}

          <div className="flex flex-wrap gap-2">
            <Button onClick={loadSheet} disabled={!scopeReady}>
              {tCount("loadList")}
            </Button>
            {scopeReady && (
              <a
                href={stockMasterCountSheetPdfUrl(scope, seasonId, locale)}
                target="_blank"
                rel="noreferrer"
                className={buttonVariants({ variant: "outline" })}
              >
                <FileText />
                {tCount("printSheet")}
              </a>
            )}
          </div>
        </CardContent>
      </Card>

      {rows !== null && (
        <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_20rem]">
          <div className="flex flex-col gap-3">
            {canCount && (
              <div className="max-w-md">
                <ProductSearch products={stock} onSelect={addProduct} karId={mode === "kar" ? karId : null} />
                <p className="mt-1 text-xs text-muted-foreground">{tCount("addHint")}</p>
              </div>
            )}
            {rows.length === 0 ? (
              <p className="rounded-md border border-dashed px-4 py-6 text-center text-sm text-muted-foreground">{tCount("empty")}</p>
            ) : (
              <div className="rounded-md border [&>div]:max-h-[65vh] [&>div]:overflow-y-auto">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead className="sticky top-0 z-20 bg-background font-bold underline">{t("common.product")}</TableHead>
                      <TableHead className="sticky top-0 z-20 bg-background font-bold underline">{t("common.bin")}</TableHead>
                      <TableHead className="sticky top-0 z-20 bg-background text-right font-bold underline">{tCount("expected")}</TableHead>
                      <TableHead className="sticky top-0 z-20 w-32 bg-background font-bold underline">{tCount("counted")}</TableHead>
                      <TableHead className="sticky top-0 z-20 bg-background text-right font-bold underline">{tCount("difference")}</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {rows.map((row) => {
                      const difference = row.counted === "" ? 0 : Number(row.counted) - row.expected;
                      return (
                        <TableRow key={row.product_id} className={cn(difference !== 0 && "bg-orange-50/60 dark:bg-orange-500/5")}>
                          <TableCell className="font-medium">{row.name}</TableCell>
                          <TableCell className="text-muted-foreground">{row.bin_label ?? t("common.noBin")}</TableCell>
                          <TableCell className="text-right tabular-nums">{row.expected}</TableCell>
                          <TableCell>
                            <Input
                              type="number"
                              min={0}
                              step={1}
                              inputMode="numeric"
                              aria-label={tCount("counted")}
                              className="w-24"
                              disabled={!canCount}
                              value={row.counted}
                              onChange={(event) =>
                                setRows((current) =>
                                  (current ?? []).map((item) =>
                                    item.product_id === row.product_id ? { ...item, counted: event.target.value } : item,
                                  ),
                                )
                              }
                            />
                          </TableCell>
                          <TableCell
                            className={cn(
                              "text-right font-semibold tabular-nums",
                              difference > 0 && "text-green-700 dark:text-green-400",
                              difference < 0 && "text-destructive",
                            )}
                          >
                            {difference > 0 ? `+${difference}` : difference === 0 ? "" : difference}
                          </TableCell>
                        </TableRow>
                      );
                    })}
                  </TableBody>
                </Table>
              </div>
            )}
          </div>

          {canCount && (
            <Card className="h-fit">
              <CardContent className="flex flex-col gap-4">
                <NamedSelect
                  id="count-reason"
                  label={t("booking.reasonLabel")}
                  value={reasonId}
                  items={countReasons}
                  emptyLabel={t("booking.chooseReason")}
                  onChange={setReasonId}
                />
                <div className="flex flex-col gap-2">
                  <Label htmlFor="count-comment">{t("booking.commentLabel")}</Label>
                  <Textarea id="count-comment" rows={2} value={comment} onChange={(event) => setComment(event.target.value)} />
                </div>
                <p className="text-sm">{tCount("differences", { count: differences.length })}</p>
                <Button size="lg" onClick={() => void handleSubmit()} disabled={differences.length === 0 || invalid || isSubmitting || seasonLocked}>
                  {t("actions.count.confirm")}
                </Button>
                <p className="text-xs text-muted-foreground">{t("booking.confirmHint")}</p>
              </CardContent>
            </Card>
          )}
        </div>
      )}
    </div>
  );
}
