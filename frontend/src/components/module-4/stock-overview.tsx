"use client";

// StockMaster's "Voorraadoverzicht": one line per product answering "where
// is it?" at a glance — Vrij · In karren · Totaal, with its bin. Click a
// line to see the split per kar (K101: 2, K043: 3). Row buttons start a
// booking with the product already filled in. Filters (search, warehouse,
// category, "only below minimum") are remembered in this browser;
// "?below=1" (from the orange banner) opens on the products below minimum.

import { Fragment, useEffect, useMemo, useState } from "react";
import { ChevronDown, ChevronRight } from "lucide-react";
import { useTranslations } from "next-intl";
import { useSearchParams } from "next/navigation";
import { Link } from "@/i18n/navigation";
import { getStockMasterLookups, getStockMasterStock } from "@/lib/api";
import type { StockMasterLookups, StockMasterMyPermissions, StockMasterProductStock } from "@/lib/types";
import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
import { buttonVariants } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { NamedSelect } from "@/components/module-4/booking-panel";
import {
  ACTION_PATHS,
  STOCKMASTER_BASE,
  canBook,
  hasRight,
  readRemembered,
  remember,
} from "@/components/module-4/stockmaster-common";

interface StockOverviewProps {
  permissions: StockMasterMyPermissions;
}

interface StockFilters {
  search: string;
  warehouseId: number | null;
  categoryId: number | null;
  belowOnly: boolean;
}

const EMPTY_FILTERS: StockFilters = { search: "", warehouseId: null, categoryId: null, belowOnly: false };

export function StockOverview({ permissions }: StockOverviewProps) {
  const t = useTranslations("stockMaster");
  const searchParams = useSearchParams();
  const [products, setProducts] = useState<StockMasterProductStock[] | null>(null);
  const [lookups, setLookups] = useState<StockMasterLookups | null>(null);
  const [failed, setFailed] = useState(false);
  const [expanded, setExpanded] = useState<Set<number>>(new Set());
  const [filters, setFilters] = useState<StockFilters>(() => {
    const remembered = readRemembered<StockFilters>("stockFilters", EMPTY_FILTERS);
    return searchParams.get("below") === "1" ? { ...remembered, belowOnly: true } : remembered;
  });

  useEffect(() => {
    getStockMasterStock()
      .then(setProducts)
      .catch(() => setFailed(true));
    getStockMasterLookups()
      .then(setLookups)
      .catch(() => setFailed(true));
  }, []);

  function updateFilters(changes: Partial<StockFilters>) {
    setFilters((current) => {
      const next = { ...current, ...changes };
      remember("stockFilters", next);
      return next;
    });
  }

  const visible = useMemo(() => {
    const needle = filters.search.trim().toLowerCase();
    return (products ?? []).filter(
      (product) =>
        (!needle || product.name.toLowerCase().includes(needle) || (product.bin_label ?? "").toLowerCase().includes(needle)) &&
        (filters.warehouseId === null || product.warehouse_id === filters.warehouseId) &&
        (filters.categoryId === null || product.category_id === filters.categoryId) &&
        (!filters.belowOnly || product.below_minimum),
    );
  }, [products, filters]);

  function toggle(productId: number) {
    setExpanded((current) => {
      const next = new Set(current);
      if (next.has(productId)) next.delete(productId);
      else next.add(productId);
      return next;
    });
  }

  const canBookIn = canBook(permissions, "book_in");
  const canBookOut = canBook(permissions, "book_out");
  const canLoad = canBook(permissions, "kar_load");
  const canSeeKars = hasRight(permissions, "kars", "view");
  const canSeeBookings = hasRight(permissions, "bookings", "view");
  const totals = visible.reduce(
    (sum, product) => ({ free: sum.free + product.free, inKars: sum.inKars + product.in_kars, total: sum.total + product.total }),
    { free: 0, inKars: 0, total: 0 },
  );

  return (
    <div className="flex flex-col gap-4">
      <div>
        <h1 className="text-2xl font-bold tracking-tight underline">{t("stock.title")}</h1>
        <p className="text-muted-foreground">{t("stock.description")}</p>
      </div>

      <div className="flex flex-wrap items-end gap-3">
        <div className="flex w-72 flex-col gap-2">
          <Label htmlFor="stock-search">{t("common.search")}</Label>
          <Input
            id="stock-search"
            autoFocus
            placeholder={t("stock.searchPlaceholder")}
            value={filters.search}
            onChange={(event) => updateFilters({ search: event.target.value })}
          />
        </div>
        <div className="w-48">
          <NamedSelect
            id="stock-warehouse"
            label={t("common.warehouse")}
            value={filters.warehouseId}
            items={lookups?.warehouses ?? []}
            emptyLabel={t("common.all")}
            onChange={(value) => updateFilters({ warehouseId: value })}
          />
        </div>
        <div className="w-48">
          <NamedSelect
            id="stock-category"
            label={t("common.category")}
            value={filters.categoryId}
            items={lookups?.categories ?? []}
            emptyLabel={t("common.all")}
            onChange={(value) => updateFilters({ categoryId: value })}
          />
        </div>
        <div className="flex h-8 items-center gap-2">
          <Checkbox
            id="stock-below"
            checked={filters.belowOnly}
            onCheckedChange={(checked) => updateFilters({ belowOnly: checked === true })}
          />
          <Label htmlFor="stock-below">{t("stock.belowOnly")}</Label>
        </div>
      </div>

      {failed && <p className="text-sm text-destructive">{t("errors.loadFailed")}</p>}
      {products === null && !failed && <p className="text-sm text-muted-foreground">{t("common.loading")}</p>}

      {products !== null && (
        <div className="rounded-md border [&>div]:max-h-[65vh] [&>div]:overflow-y-auto">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="sticky top-0 z-20 w-8 bg-background" />
                <TableHead className="sticky top-0 z-20 bg-background font-bold underline">{t("common.product")}</TableHead>
                <TableHead className="sticky top-0 z-20 bg-background font-bold underline">{t("common.bin")}</TableHead>
                <TableHead className="sticky top-0 z-20 bg-background text-right font-bold underline">{t("stock.free")}</TableHead>
                <TableHead className="sticky top-0 z-20 bg-background text-right font-bold underline">{t("stock.inKars")}</TableHead>
                <TableHead className="sticky top-0 z-20 bg-background text-right font-bold underline">{t("stock.total")}</TableHead>
                <TableHead className="sticky top-0 z-20 bg-background text-right font-bold underline">{t("stock.minimum")}</TableHead>
                <TableHead className="sticky top-0 right-0 z-30 bg-background text-right font-bold underline">
                  {t("common.actions")}
                </TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {visible.length === 0 && (
                <TableRow>
                  <TableCell colSpan={8} className="py-8 text-center text-muted-foreground">
                    {t("stock.empty")}
                  </TableCell>
                </TableRow>
              )}
              {visible.map((product) => {
                const isOpen = expanded.has(product.product_id);
                return (
                  <Fragment key={product.product_id}>
                    <TableRow className="group cursor-pointer" onClick={() => toggle(product.product_id)}>
                      <TableCell>
                        {isOpen ? <ChevronDown className="size-4" /> : <ChevronRight className="size-4" />}
                      </TableCell>
                      <TableCell>
                        <div className="flex flex-wrap items-center gap-2">
                          <span className="font-medium">{product.name}</span>
                          {product.below_minimum && (
                            <Badge className="bg-orange-100 text-orange-800 dark:bg-orange-500/15 dark:text-orange-300">
                              {t("stock.belowMinimum")}
                            </Badge>
                          )}
                          {product.is_blocked && <Badge variant="destructive">{t("common.blocked")}</Badge>}
                          {product.is_consumable && <Badge variant="secondary">{t("stock.consumable")}</Badge>}
                        </div>
                      </TableCell>
                      <TableCell className="text-muted-foreground">{product.bin_label ?? t("common.noBin")}</TableCell>
                      <TableCell className="text-right tabular-nums">{product.free}</TableCell>
                      <TableCell className="text-right tabular-nums">{product.in_kars}</TableCell>
                      <TableCell className="text-right font-semibold tabular-nums">{product.total}</TableCell>
                      <TableCell className="text-right tabular-nums text-muted-foreground">{product.min_stock ?? ""}</TableCell>
                      <TableCell
                        className="sticky right-0 z-10 bg-background text-right group-hover:bg-muted/50"
                        onClick={(event) => event.stopPropagation()}
                      >
                        <div className="flex justify-end gap-1">
                          {canBookIn && (
                            <Link
                              href={`${STOCKMASTER_BASE}${ACTION_PATHS.book_in}?product=${product.product_id}`}
                              className={buttonVariants({ variant: "outline", size: "xs" })}
                            >
                              {t("actions.book_in.title")}
                            </Link>
                          )}
                          {canLoad && (
                            <Link
                              href={`${STOCKMASTER_BASE}${ACTION_PATHS.kar_load}?product=${product.product_id}`}
                              className={buttonVariants({ variant: "outline", size: "xs" })}
                            >
                              {t("stock.loadInKar")}
                            </Link>
                          )}
                          {canBookOut && (
                            <Link
                              href={`${STOCKMASTER_BASE}${ACTION_PATHS.book_out}?product=${product.product_id}`}
                              className={buttonVariants({ variant: "outline", size: "xs" })}
                            >
                              {t("actions.book_out.title")}
                            </Link>
                          )}
                        </div>
                      </TableCell>
                    </TableRow>
                    {isOpen && (
                      <TableRow className="bg-muted/30 hover:bg-muted/30">
                        <TableCell />
                        <TableCell colSpan={7}>
                          <div className="flex flex-wrap items-center gap-2 text-sm">
                            <span className="text-muted-foreground">
                              {product.kars.length > 0 ? t("stock.perKar") : t("stock.noKars")}
                            </span>
                            {product.kars.map((kar) => (
                              <span key={kar.kar_id} className="rounded-md border bg-background px-2 py-0.5">
                                {canSeeKars ? (
                                  <Link href={`${STOCKMASTER_BASE}/kars/${kar.kar_id}`} className="font-semibold underline">
                                    {kar.kar_nummer}
                                  </Link>
                                ) : (
                                  <span className="font-semibold">{kar.kar_nummer}</span>
                                )}
                                : {kar.quantity}
                              </span>
                            ))}
                            {canSeeBookings && (
                              <Link
                                href={`${STOCKMASTER_BASE}/bookings?product=${product.product_id}`}
                                className={cn(buttonVariants({ variant: "link", size: "xs" }), "ml-auto")}
                              >
                                {t("stock.history")}
                              </Link>
                            )}
                          </div>
                        </TableCell>
                      </TableRow>
                    )}
                  </Fragment>
                );
              })}
              {visible.length > 0 && (
                <TableRow className="font-semibold hover:bg-transparent">
                  <TableCell />
                  <TableCell colSpan={2}>{t("stock.totals", { count: visible.length })}</TableCell>
                  <TableCell className="text-right tabular-nums">{totals.free}</TableCell>
                  <TableCell className="text-right tabular-nums">{totals.inKars}</TableCell>
                  <TableCell className="text-right tabular-nums">{totals.total}</TableCell>
                  <TableCell colSpan={2} />
                </TableRow>
              )}
            </TableBody>
          </Table>
        </div>
      )}
    </div>
  );
}
