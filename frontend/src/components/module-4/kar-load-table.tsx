"use client";

// Kar laden's "Karinhoud" table: one row per product AND source ("Bron") of
// the chosen kar — a product with a kar need and also added by hand shows on
// two rows, one "Altsien Select" and one "Manueel" (manual requests are stored
// per season + kar and come with the kar detail). Each row shows what was
// asked and granted, what's free in the warehouse, what's in the kar (and
// consumed outside the warehouse this season), what may be delivered now and
// the quantity to load ("Nu te leveren"). The number column titles are turned
// 90° to the left to save width and explained in a tooltip; all columns are
// centered. A checkbox per row (and "select all") drives "Vul aan met wat
// ontbreekt" and "Verwijder geselecteerde".
//
// The rows are built here (buildKarLoadRows) from the kar detail and the
// panel's basket, so the table and the panel's buttons always use the same
// numbers. The booking itself sums the rows per product.

import { Trash2, Workflow } from "lucide-react";
import { useTranslations } from "next-intl";
import { useState } from "react";
import type {
  StockMasterEntitlementTrace,
  StockMasterKarDetail,
  StockMasterKarLine,
  StockMasterProductStock,
} from "@/lib/types";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";
import { AvailabilityFlowDialog } from "@/components/module-4/availability-flow-dialog";
import { ProductThumb } from "@/components/module-4/product-thumb";

/** Where a row's request comes from ("interventions" is reserved for later). */
export type KarLoadSource = "altsien" | "manual" | "interventions";

/** The part of a basket line the table needs (the panel's BasketLine fits): a
 *  row's "Nu te leveren". On Kar laden a line without a source belongs to the
 *  product's kar-need row, a "manual" line to its Manueel row. */
export interface KarLoadBasketLine {
  productId: number;
  quantity: number;
  source?: KarLoadSource;
}

/** A row's identity: product + where its line came from (the kar-need row has no source). */
export function karLoadRowKey(productId: number, source?: KarLoadSource): string {
  return `${productId}:${source ?? "kar"}`;
}

/** One row of the table. */
export interface KarLoadRow {
  key: string;
  productId: number;
  /** The basket line's source: "manual" for a Manueel row, undefined for the kar-need row. */
  lineSource: KarLoadSource | undefined;
  /** The stored manual request behind a Manueel row. */
  requestId: number | null;
  name: string;
  binLabel: string | null;
  /** The product's stock row (picture, free stock); missing only while loading. */
  product: StockMasterProductStock | undefined;
  /** What the Bron column shows. */
  source: KarLoadSource | null;
  /** Gevraagd door Vereniging: the need on the Altsien row, the manual pieces on a Manueel row. */
  requested: number;
  /** Initieel Toegekend door Altsien kernlid = the kar need of this season (0 on a Manueel row). */
  granted: number;
  free: number;
  inKar: number;
  consumedOutside: number;
  /** Manueel row: pieces of its request already delivered (in the kar or consumed beyond the need). */
  delivered: number;
  /** "Nu te leveren" of the product's other rows (they share the same free pieces). */
  otherQuantity: number;
  /** What this row may get by the flow diagram (backend), before the physical stock. */
  entitled: number;
  /** How the backend worked `entitled` out, drawn by the flow dialog (null: no request). */
  trace: StockMasterEntitlementTrace | null;
  /** Op dit moment beschikbaar voor levering (see availableForDelivery). */
  availableNow: number;
  /** Nu te leveren. */
  quantity: number;
  isBlocked: boolean;
}

type AvailabilityInput = Pick<
  KarLoadRow,
  "source" | "requested" | "entitled" | "consumedOutside" | "inKar" | "free" | "delivered" | "otherQuantity"
>;

/** "Op dit moment beschikbaar voor levering". The backend's flow diagram gives
 *  what the row may get (`entitled`: Blokkeer, logistiek product, Limiet,
 *  Maximum initiële stock — see module_4/delivery_entitlement.py); here that is
 *  limited to what's physically there. Free stock already taken by the
 *  product's other rows doesn't count.
 *  - Manueel row: entitled minus what it already got, at most the free stock left.
 *  - Other rows: entitled minus what was already consumed outside the warehouse,
 *    at most what can be in the kar after loading (already in it + free stock left).
 *  Never below 0. Change it only here: the table, the flow dialog and "Vul aan
 *  met wat ontbreekt" all use it. */
export function availableForDelivery(row: AvailabilityInput): number {
  const freeLeft = row.free - row.otherQuantity;
  if (row.source === "manual") return Math.max(Math.min(row.entitled - row.delivered, freeLeft), 0);
  return Math.max(Math.min(row.entitled - row.consumedOutside, row.inKar + freeLeft), 0);
}

/** What "Vul aan met wat ontbreekt" puts in "Nu te leveren": on a Manueel row
 *  what's available now; otherwise available now − already in the kar (those
 *  pieces belong to the kar-need row). */
export function fillQuantity(row: AvailabilityInput): number {
  const available = availableForDelivery(row);
  return row.source === "manual" ? available : Math.max(available - row.inKar, 0);
}

/** "Vul aan met wat ontbreekt" for the checked rows, one after the other so two
 *  rows of the same product never take the same free pieces. Returns the new
 *  "Nu te leveren" per row key (blocked products are skipped). */
export function fillCheckedRows(rows: KarLoadRow[], checked: Set<string>): Map<string, number> {
  const quantities = new Map(rows.map((row) => [row.key, row.quantity]));
  const filled = new Map<string, number>();
  for (const row of rows) {
    if (!checked.has(row.key) || row.isBlocked) continue;
    // What the product's other rows deliver, with the values filled so far.
    const otherQuantity = rows
      .filter((other) => other.productId === row.productId && other.key !== row.key)
      .reduce((sum, other) => sum + (quantities.get(other.key) ?? 0), 0);
    const quantity = fillQuantity({ ...row, otherQuantity });
    quantities.set(row.key, quantity);
    filled.set(row.key, quantity);
  }
  return filled;
}

// Rows sort by name, then source (Altsien Select, Manueel, Interventies, none), so a
// product's rows stay together.
const SOURCE_ORDER: Record<KarLoadSource, number> = { altsien: 0, manual: 1, interventions: 2 };

/** The table's rows: every product with a need, in the kar or consumed outside (its
 *  kar-need row), plus one Manueel row per stored manual request. */
export function buildKarLoadRows(
  detail: StockMasterKarDetail,
  lines: KarLoadBasketLine[],
  productsById: Map<number, StockMasterProductStock>,
): KarLoadRow[] {
  const karLines = new Map<number, StockMasterKarLine>(detail.lines.map((line) => [line.product_id, line]));
  const basket = new Map(lines.map((line) => [karLoadRowKey(line.productId, line.source), line]));
  const requests = new Map(detail.manual_requests.map((request) => [request.product_id, request]));
  // A kar that's out holds nothing in the warehouse: "Reeds in kar" is then what left with it
  // ("Kar vertrekt" + follow-up deliveries).
  const isOut = detail.kar.is_out;
  const leftWith = new Map(detail.dispatched.map((line) => [line.product_id, line]));
  // "Nu te leveren" per product over all its rows.
  const totals = new Map<number, number>();
  for (const line of lines) totals.set(line.productId, (totals.get(line.productId) ?? 0) + line.quantity);

  // The rows to show: the kar-need row of each kar line, a Manueel row per manual request, and
  // a row for a basket line without either (e.g. ?prefill=). A manual line whose request is gone isn't shown.
  const keys = new Map<string, { productId: number; lineSource: KarLoadSource | undefined }>();
  const karProductIds = new Set<number>([...karLines.keys(), ...(isOut ? leftWith.keys() : [])]);
  for (const productId of karProductIds) {
    // A product without a need but with a manual request: what's in the kar belongs to its
    // Manueel row (which shows it), so no second, empty row — unless that row is being delivered.
    const deliversOnKarRow = (basket.get(karLoadRowKey(productId))?.quantity ?? 0) > 0;
    if ((karLines.get(productId)?.required ?? 0) === 0 && requests.has(productId) && !deliversOnKarRow) continue;
    keys.set(karLoadRowKey(productId), { productId, lineSource: undefined });
  }
  for (const productId of requests.keys()) keys.set(karLoadRowKey(productId, "manual"), { productId, lineSource: "manual" });
  for (const line of lines) {
    if (line.source !== "manual") keys.set(karLoadRowKey(line.productId, line.source), { productId: line.productId, lineSource: line.source });
  }

  const rows: KarLoadRow[] = [];
  for (const [key, { productId, lineSource }] of keys) {
    const karLine = karLines.get(productId);
    const line = basket.get(key);
    const product = productsById.get(productId);
    const name = karLine?.name ?? product?.name ?? leftWith.get(productId)?.name;
    // A basket product whose stock row hasn't arrived yet can't be shown.
    if (name === undefined) continue;

    const isManual = lineSource === "manual";
    const request = isManual ? requests.get(productId) : undefined;
    const need = karLine?.required ?? 0;
    // The kar need belongs to the kar-need row; a Manueel row asks only its manual pieces.
    const granted = isManual ? 0 : need;
    const source: KarLoadSource | null = isManual ? "manual" : granted > 0 ? "altsien" : (lineSource ?? null);
    const quantity = line?.quantity ?? 0;
    const requested = isManual ? (request?.quantity ?? 0) : granted;
    const inKar = isOut ? (leftWith.get(productId)?.quantity ?? 0) : (karLine?.in_kar ?? 0);
    const consumedOutside = karLine?.consumed_outside ?? 0;
    // The flow diagram's outcome for this row: a Manueel row has its own, the kar-need row the kar line's.
    const trace = (isManual ? request?.entitlement_trace : karLine?.entitlement_trace) ?? null;
    const values: AvailabilityInput = {
      source,
      requested,
      entitled: trace?.entitled ?? 0,
      consumedOutside,
      inKar,
      free: product?.free ?? karLine?.free_available ?? 0,
      // What the kar holds (or used) beyond its need counts for the manual request.
      delivered: isManual ? Math.min(Math.max(inKar + consumedOutside - need, 0), requested) : 0,
      otherQuantity: (totals.get(productId) ?? 0) - quantity,
    };
    rows.push({
      key,
      productId,
      lineSource,
      requestId: request?.id ?? null,
      name,
      binLabel: karLine?.bin_label ?? product?.bin_label ?? null,
      product,
      granted,
      ...values,
      trace,
      availableNow: availableForDelivery(values),
      quantity,
      isBlocked: karLine?.is_blocked ?? product?.is_blocked ?? false,
    });
  }

  rows.sort((a, b) => {
    const order = (row: KarLoadRow) => (row.source === null ? 9 : SOURCE_ORDER[row.source]);
    return a.name.localeCompare(b.name) || order(a) - order(b);
  });
  return rows;
}

/** "Before → after" of one place a row touches (from the panel's placeChanges). */
export interface KarLoadPlaceChange {
  label: string;
  before: number;
  after: number;
}

interface KarLoadTableProps {
  rows: KarLoadRow[];
  /** The checked rows' keys. */
  selected: Set<string>;
  onToggle: (key: string, checked: boolean) => void;
  onToggleAll: (checked: boolean) => void;
  onQuantityChange: (row: KarLoadRow, quantity: number) => void;
  onRemove: (row: KarLoadRow) => void;
  /** The panel's check of a row's product ("not enough", "blocked"), or null. */
  lineProblem: (row: KarLoadRow) => string | null;
  /** The panel's "before → after" of a row's product. */
  placeChanges: (row: KarLoadRow) => KarLoadPlaceChange[];
}

// Sticky header cell classes (bold + underlined, opaque while scrolling, title centered at the bottom).
const HEAD = "sticky top-0 z-20 h-auto bg-background px-1.5 text-center align-bottom font-bold underline";

// The number columns in display order (translations under stockMaster.karLoad.columns.*).
const NUMBER_COLUMNS = ["requested", "granted", "free", "inKar", "consumedOutside", "availableNow"] as const;

export function KarLoadTable({
  rows,
  selected,
  onToggle,
  onToggleAll,
  onQuantityChange,
  onRemove,
  lineProblem,
  placeChanges,
}: KarLoadTableProps) {
  const t = useTranslations("stockMaster");
  // The row whose "Op dit moment beschikbaar" calculation is shown in the flow dialog.
  const [flowKey, setFlowKey] = useState<string | null>(null);
  const flowRow = rows.find((row) => row.key === flowKey) ?? null;

  if (rows.length === 0) {
    return <p className="rounded-md border border-dashed px-4 py-6 text-center text-sm text-muted-foreground">{t("karLoad.emptyTable")}</p>;
  }

  const checkedCount = rows.filter((row) => selected.has(row.key)).length;
  const allChecked = checkedCount === rows.length;

  return (
    <TooltipProvider delay={200}>
      <div className="rounded-md border [&>div]:max-h-[70vh] [&>div]:overflow-y-auto">
        <Table>
          <TableHeader>
            <TableRow>
              {/* "Select all": checked when every row is, half when some are. */}
              <TableHead className={cn(HEAD, "w-8 pb-2.5")}>
                <Checkbox
                  className="mx-auto"
                  checked={allChecked}
                  indeterminate={checkedCount > 0 && !allChecked}
                  onCheckedChange={(checked) => onToggleAll(checked)}
                  aria-label={t("karLoad.selectAll")}
                />
              </TableHead>
              {/* Bron and Producten read horizontally; the number columns are turned. */}
              <ColumnHead column="source" horizontal />
              <TableHead className={cn(HEAD, "pb-2")}>{t("karLoad.columns.products")}</TableHead>
              {NUMBER_COLUMNS.map((column) => (
                <ColumnHead key={column} column={column} />
              ))}
              <ColumnHead column="deliverNow" />
              <ColumnHead column="preview" />
            </TableRow>
          </TableHeader>
          <TableBody>
            {rows.map((row) => {
              const problem = row.quantity > 0 ? lineProblem(row) : null;
              const numbers: Record<(typeof NUMBER_COLUMNS)[number], number> = {
                requested: row.requested,
                granted: row.granted,
                free: row.free,
                inKar: row.inKar,
                consumedOutside: row.consumedOutside,
                availableNow: row.availableNow,
              };
              return (
                <TableRow key={row.key} className="group" data-state={selected.has(row.key) ? "selected" : undefined}>
                  <TableCell className="px-1.5 text-center">
                    <Checkbox
                      className="mx-auto"
                      checked={selected.has(row.key)}
                      onCheckedChange={(checked) => onToggle(row.key, checked)}
                      aria-label={t("karLoad.selectRow", { name: row.name })}
                    />
                  </TableCell>
                  <TableCell className="px-1.5 text-center text-sm">{row.source ? t(`karLoad.sources.${row.source}`) : ""}</TableCell>
                  {/* Picture with the name and bin next to it, centered under the title. */}
                  <TableCell className="px-1.5">
                    <div className="flex items-center justify-center gap-3">
                      <ProductThumb productId={row.productId} name={row.name} product={row.product} />
                      <div className="min-w-0">
                        <div className="max-w-64 truncate font-medium" title={row.name}>
                          {row.name}
                        </div>
                        <div className="text-xs text-muted-foreground">{row.binLabel ?? t("common.noBin")}</div>
                      </div>
                    </div>
                  </TableCell>
                  {NUMBER_COLUMNS.map((column) => (
                    <TableCell
                      key={column}
                      className={cn(
                        "px-1.5 text-center tabular-nums",
                        // "Reeds in kar buiten magazijn" in dark green so it stands out, also when 0.
                        column === "consumedOutside"
                          ? "font-semibold text-green-800 dark:text-green-400"
                          : numbers[column] === 0 && "text-muted-foreground",
                        // Extra room on the right for the flow button.
                        column === "availableNow" && "pr-7 pl-1.5 font-semibold",
                      )}
                    >
                      {column === "availableNow" ? (
                        // The value stays centered; the button that shows how it was worked out sits to its right.
                        <span className="relative inline-block">
                          {numbers[column]}
                          <Button
                            variant="ghost"
                            size="icon-xs"
                            className="absolute top-1/2 left-full ml-0.5 -translate-y-1/2 text-muted-foreground"
                            onClick={() => setFlowKey(row.key)}
                            aria-label={t("karLoad.flow.open")}
                            title={t("karLoad.flow.open")}
                          >
                            <Workflow />
                          </Button>
                        </span>
                      ) : (
                        numbers[column]
                      )}
                    </TableCell>
                  ))}
                  {/* Nu te leveren: the booking's quantity, typed or filled by "Vul aan met wat ontbreekt". */}
                  {/* Extra room on the right for a Manueel row's delete button, so every input stays centered. */}
                  <TableCell className="px-1.5 pr-9">
                    <div className="relative mx-auto w-20">
                      <Input
                        type="number"
                        min={0}
                        step={1}
                        inputMode="numeric"
                        aria-label={t("karLoad.columns.deliverNow")}
                        className={cn("w-20 text-center", problem && "border-destructive")}
                        value={row.quantity}
                        onChange={(event) => onQuantityChange(row, Math.max(0, Number.parseInt(event.target.value, 10) || 0))}
                      />
                      {/* Only a Manueel row can disappear; the others hold a need or kar contents. */}
                      {row.source === "manual" && (
                        <Button
                          variant="ghost"
                          size="icon-sm"
                          className="absolute top-1/2 left-full ml-1 -translate-y-1/2"
                          onClick={() => onRemove(row)}
                          aria-label={t("booking.removeLine")}
                        >
                          <Trash2 />
                        </Button>
                      )}
                    </div>
                    {problem && (
                      <div className="mx-auto mt-1 max-w-48 text-center text-xs font-medium whitespace-normal text-destructive">{problem}</div>
                    )}
                  </TableCell>
                  {/* Voor → na per place for the product, only while this row delivers something. */}
                  <TableCell className="px-1.5 text-center text-sm tabular-nums">
                    {row.quantity > 0 &&
                      placeChanges(row).map((change) => (
                        <div key={change.label} className={cn(change.after < 0 && "text-destructive")}>
                          <span className="text-muted-foreground">{change.label}</span> {change.before} →{" "}
                          <strong>{change.after}</strong>
                        </div>
                      ))}
                  </TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      </div>
      <AvailabilityFlowDialog row={flowRow} onClose={() => setFlowKey(null)} />
    </TooltipProvider>
  );
}

/** A column title with the full title and its explanation in a tooltip; turned 90° to the
 *  left (reads bottom to top) unless `horizontal`. */
function ColumnHead({ column, horizontal = false }: { column: string; horizontal?: boolean }) {
  const t = useTranslations("stockMaster.karLoad.columns");
  return (
    <TableHead className={cn(HEAD, horizontal && "pb-2")}>
      <Tooltip>
        <TooltipTrigger
          render={
            // max-h lets the long turned titles wrap onto a second vertical line instead of making the header very tall.
            <span
              tabIndex={0}
              className={cn(
                "inline-block cursor-help",
                !horizontal && "max-h-40 rotate-180 py-1 text-left whitespace-normal [writing-mode:vertical-rl]",
              )}
            />
          }
        >
          {t(column)}
        </TooltipTrigger>
        <TooltipContent className="max-w-xs text-sm font-normal no-underline">
          <div className="font-semibold">{t(column)}</div>
          <div>{t(`${column}Help`)}</div>
        </TooltipContent>
      </Tooltip>
    </TableHead>
  );
}
