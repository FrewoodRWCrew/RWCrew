"use client";

// StockMaster's "Te bestellen": per product, this season's needs (all
// kars together) against what's in stock (free + in kars), and what's left
// to order. Tick the lines that were ordered and "Inboeken" opens the
// booking panel pre-filled with those quantities, so on delivery only the
// differences need correcting. Also printable (Bestellijst PDF) and
// exportable (CSV, opens in Excel).

import { useEffect, useMemo, useState } from "react";
import { Download, FileText, PackagePlus } from "lucide-react";
import { useLocale, useTranslations } from "next-intl";
import { toast } from "sonner";
import { useRouter } from "@/i18n/navigation";
import { getStockMasterLookups, getStockMasterOrderNeeds, stockMasterOrderListPdfUrl } from "@/lib/api";
import type { Season, StockMasterLookups, StockMasterMyPermissions, StockMasterOrderNeed } from "@/lib/types";
import { cn } from "@/lib/utils";
import { Button, buttonVariants } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Label } from "@/components/ui/label";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { NamedSelect } from "@/components/module-4/booking-panel";
import { StockMasterSeasonSelect, useStockMasterSeasonId } from "@/components/module-4/stockmaster-season-select";
import { ACTION_PATHS, STOCKMASTER_BASE, canBook, stockErrorMessage } from "@/components/module-4/stockmaster-common";

interface OrderNeedsProps {
  seasons: Season[];
  permissions: StockMasterMyPermissions;
}

export function OrderNeeds({ seasons, permissions }: OrderNeedsProps) {
  const t = useTranslations("stockMaster");
  const tOrder = useTranslations("stockMaster.orderNeeds");
  const locale = useLocale();
  const router = useRouter();
  const seasonId = useStockMasterSeasonId(seasons);

  const [lookups, setLookups] = useState<StockMasterLookups | null>(null);
  const [warehouseId, setWarehouseId] = useState<number | null>(null);
  const [categoryId, setCategoryId] = useState<number | null>(null);
  const [onlyToOrder, setOnlyToOrder] = useState(true);
  const [rows, setRows] = useState<StockMasterOrderNeed[] | null>(null);
  const [picked, setPicked] = useState<Set<number>>(new Set());

  useEffect(() => {
    getStockMasterLookups()
      .then(setLookups)
      .catch(() => toast.error(t("errors.loadFailed")));
  }, [t]);

  useEffect(() => {
    if (seasonId === null) return;
    getStockMasterOrderNeeds(seasonId, warehouseId, categoryId)
      .then((result) => {
        setRows(result);
        // Everything that must be ordered starts ticked.
        setPicked(new Set(result.filter((row) => row.to_order > 0).map((row) => row.product_id)));
      })
      .catch((error) => toast.error(stockErrorMessage(t, error)));
  }, [seasonId, warehouseId, categoryId, t]);

  const visible = useMemo(() => (rows ?? []).filter((row) => !onlyToOrder || row.to_order > 0), [rows, onlyToOrder]);
  const pickedRows = visible.filter((row) => picked.has(row.product_id) && row.to_order > 0);
  const canBookIn = canBook(permissions, "book_in");

  function bookInPicked() {
    const prefill = pickedRows.map((row) => `${row.product_id}:${row.to_order}`).join(",");
    router.push(`${STOCKMASTER_BASE}${ACTION_PATHS.book_in}?prefill=${prefill}${seasonId ? `&season=${seasonId}` : ""}`);
  }

  /** The visible list as a CSV file (semicolons, so Excel in Belgium opens it right). */
  function exportCsv() {
    const header = [t("common.product"), t("common.category"), t("common.warehouse"), t("common.bin"), tOrder("needed"), t("stock.free"), t("stock.inKars"), tOrder("inStock"), tOrder("toOrder")];
    const lines = visible.map((row) =>
      [row.name, row.category_name ?? "", row.warehouse_name ?? "", row.bin_label ?? "", row.needed, row.free, row.in_kars, row.in_stock, row.to_order]
        .map((value) => `"${String(value).replaceAll('"', '""')}"`)
        .join(";"),
    );
    const blob = new Blob([`﻿${[header.join(";"), ...lines].join("\r\n")}`], { type: "text/csv;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `${tOrder("fileName")}.csv`;
    link.click();
    URL.revokeObjectURL(url);
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight underline">{tOrder("title")}</h1>
          <p className="text-muted-foreground">{tOrder("description")}</p>
        </div>
        <StockMasterSeasonSelect seasons={seasons} seasonId={seasonId} />
      </div>

      <div className="flex flex-wrap items-end gap-3">
        <div className="w-48">
          <NamedSelect
            id="order-warehouse"
            label={t("common.warehouse")}
            value={warehouseId}
            items={lookups?.warehouses ?? []}
            emptyLabel={t("common.all")}
            onChange={setWarehouseId}
          />
        </div>
        <div className="w-48">
          <NamedSelect
            id="order-category"
            label={t("common.category")}
            value={categoryId}
            items={lookups?.categories ?? []}
            emptyLabel={t("common.all")}
            onChange={setCategoryId}
          />
        </div>
        <div className="flex h-8 items-center gap-2">
          <Checkbox id="order-only" checked={onlyToOrder} onCheckedChange={(checked) => setOnlyToOrder(checked === true)} />
          <Label htmlFor="order-only">{tOrder("onlyToOrder")}</Label>
        </div>
        <div className="ml-auto flex flex-wrap gap-2">
          {canBookIn && (
            <Button onClick={bookInPicked} disabled={pickedRows.length === 0}>
              <PackagePlus />
              {tOrder("bookIn", { count: pickedRows.length })}
            </Button>
          )}
          {seasonId !== null && (
            <a
              href={stockMasterOrderListPdfUrl(seasonId, warehouseId, categoryId, locale)}
              target="_blank"
              rel="noreferrer"
              className={buttonVariants({ variant: "outline" })}
            >
              <FileText />
              {tOrder("printList")}
            </a>
          )}
          <Button variant="outline" onClick={exportCsv} disabled={visible.length === 0}>
            <Download />
            {tOrder("export")}
          </Button>
        </div>
      </div>

      {rows === null ? (
        <p className="text-sm text-muted-foreground">{t("common.loading")}</p>
      ) : (
        <div className="rounded-md border [&>div]:max-h-[65vh] [&>div]:overflow-y-auto">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="sticky top-0 z-20 w-10 bg-background" />
                <TableHead className="sticky top-0 z-20 bg-background font-bold underline">{t("common.product")}</TableHead>
                <TableHead className="sticky top-0 z-20 bg-background font-bold underline">{t("common.category")}</TableHead>
                <TableHead className="sticky top-0 z-20 bg-background font-bold underline">{t("common.bin")}</TableHead>
                <TableHead className="sticky top-0 z-20 bg-background text-right font-bold underline">{tOrder("needed")}</TableHead>
                <TableHead className="sticky top-0 z-20 bg-background text-right font-bold underline">{t("stock.free")}</TableHead>
                <TableHead className="sticky top-0 z-20 bg-background text-right font-bold underline">{t("stock.inKars")}</TableHead>
                <TableHead className="sticky top-0 z-20 bg-background text-right font-bold underline">{tOrder("toOrder")}</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {visible.length === 0 && (
                <TableRow>
                  <TableCell colSpan={8} className="py-8 text-center text-muted-foreground">
                    {rows.length === 0 ? tOrder("noNeeds") : tOrder("nothingToOrder")}
                  </TableCell>
                </TableRow>
              )}
              {visible.map((row) => (
                <TableRow key={row.product_id}>
                  <TableCell>
                    {row.to_order > 0 && (
                      <Checkbox
                        aria-label={row.name}
                        checked={picked.has(row.product_id)}
                        onCheckedChange={(checked) =>
                          setPicked((current) => {
                            const next = new Set(current);
                            if (checked === true) next.add(row.product_id);
                            else next.delete(row.product_id);
                            return next;
                          })
                        }
                      />
                    )}
                  </TableCell>
                  <TableCell className="font-medium">{row.name}</TableCell>
                  <TableCell className="text-muted-foreground">{row.category_name ?? ""}</TableCell>
                  <TableCell className="text-muted-foreground">{row.bin_label ?? t("common.noBin")}</TableCell>
                  <TableCell className="text-right tabular-nums">{row.needed}</TableCell>
                  <TableCell className="text-right tabular-nums">{row.free}</TableCell>
                  <TableCell className="text-right tabular-nums">{row.in_kars}</TableCell>
                  <TableCell
                    className={cn(
                      "text-right font-bold tabular-nums",
                      row.to_order > 0 ? "text-orange-700 dark:text-orange-300" : "text-green-700 dark:text-green-400",
                    )}
                  >
                    {row.to_order}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}
    </div>
  );
}
