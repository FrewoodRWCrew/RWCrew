"use client";

// StockMaster's "Kar inventarissen": the counts teams made of their own kar on
// the public kar page (karblad QR code → Kar inventaris), newest first, for the
// chosen season — date (Belgian time), kar, team, who counted, what left with
// the kar versus what was counted, and the difference. A row opens to show its
// products and the remark. Text filters above every column (client-side);
// Excel downloads the rows shown. Read-only and informative: nothing here
// changes stock.

import { Fragment, useState } from "react";
import { ChevronDown, ChevronRight, Download } from "lucide-react";
import { useLocale, useTranslations } from "next-intl";
import { toast } from "sonner";

import { exportStockMasterKarInventories, listStockMasterKarInventories } from "@/lib/api";
import { formatDateTime } from "@/lib/date-time";
import type { KarInventory, Season } from "@/lib/types";
import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { FilterHeadCell, useColumnFilters } from "@/components/module-5/column-filters";
import { saveExcel } from "@/components/module-5/desk-common";
import { StockMasterSeasonSelect, useStockMasterSeasonId } from "@/components/module-4/stockmaster-season-select";
import { useKeyedLoad } from "@/components/module-4/use-keyed-load";

const HEAD_CLASS = "sticky top-0 z-20 bg-background font-bold underline";

type FilterKey = "date" | "kar" | "team" | "countedBy" | "remark";

/** The difference counted − left with the kar, coloured like the public screen. */
function DifferenceBadge({ difference }: { difference: number }) {
  if (difference === 0) return <Badge className="bg-green-600 text-white">0</Badge>;
  return (
    <Badge className={cn("text-white", difference < 0 ? "bg-orange-600" : "bg-blue-600")}>
      {difference > 0 ? `+${difference}` : difference}
    </Badge>
  );
}

export function KarInventoriesList({ seasons }: { seasons: Season[] }) {
  const t = useTranslations("stockMaster");
  const tList = useTranslations("stockMaster.karInventories");
  const locale = useLocale();
  const seasonId = useStockMasterSeasonId(seasons);
  const inventories = useKeyedLoad(seasonId === null ? null : String(seasonId), () =>
    listStockMasterKarInventories(seasonId!),
  );
  const [openIds, setOpenIds] = useState<Set<number>>(new Set());
  const [isDownloading, setIsDownloading] = useState(false);
  const { filters, setFilter, matches } = useColumnFilters<FilterKey>();

  // The rows that pass the column filters.
  const shown = (inventories.data ?? []).filter((inventory) =>
    matches({
      date: formatDateTime(inventory.created_at),
      kar: inventory.kar_nummer,
      team: inventory.team_name,
      countedBy: inventory.counted_by_name,
      remark: inventory.remark,
    }),
  );

  function toggle(id: number) {
    setOpenIds((current) => {
      const next = new Set(current);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  async function handleDownload() {
    setIsDownloading(true);
    try {
      const blob = await exportStockMasterKarInventories(
        shown.map((inventory) => inventory.id),
        locale,
      );
      saveExcel(blob, "stockmaster-kar-inventarissen", seasons.find((season) => season.id === seasonId)?.name ?? "");
    } catch {
      toast.error(tList("downloadFailed"));
    } finally {
      setIsDownloading(false);
    }
  }

  return (
    <div className="flex flex-col gap-4">
      <div>
        <h1 className="text-2xl font-bold tracking-tight underline">{tList("title")}</h1>
        <p className="text-muted-foreground">{tList("description")}</p>
      </div>

      <div className="flex flex-wrap items-end justify-between gap-3">
        <StockMasterSeasonSelect seasons={seasons} seasonId={seasonId} />
        <Button variant="outline" onClick={handleDownload} disabled={isDownloading || shown.length === 0}>
          <Download />
          {tList("download")}
        </Button>
      </div>

      {inventories.failed ? (
        <p className="text-sm text-destructive">{t("errors.loadFailed")}</p>
      ) : inventories.data === null ? (
        <p className="text-sm text-muted-foreground">{t("common.loading")}</p>
      ) : (
        <div className="rounded-md border [&>div]:max-h-[65vh] [&>div]:overflow-y-auto">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className={HEAD_CLASS}>{tList("date")}</TableHead>
                <TableHead className={HEAD_CLASS}>{t("common.kar")}</TableHead>
                <TableHead className={HEAD_CLASS}>{tList("team")}</TableHead>
                <TableHead className={HEAD_CLASS}>{tList("countedBy")}</TableHead>
                <TableHead className={`${HEAD_CLASS} text-right`}>{tList("expected")}</TableHead>
                <TableHead className={`${HEAD_CLASS} text-right`}>{tList("counted")}</TableHead>
                <TableHead className={`${HEAD_CLASS} text-right`}>{tList("difference")}</TableHead>
                <TableHead className={HEAD_CLASS}>{tList("remark")}</TableHead>
              </TableRow>
              <TableRow>
                <FilterHeadCell label={tList("date")} value={filters.date} onChange={(value) => setFilter("date", value)} />
                <FilterHeadCell label={t("common.kar")} value={filters.kar} onChange={(value) => setFilter("kar", value)} />
                <FilterHeadCell label={tList("team")} value={filters.team} onChange={(value) => setFilter("team", value)} />
                <FilterHeadCell
                  label={tList("countedBy")}
                  value={filters.countedBy}
                  onChange={(value) => setFilter("countedBy", value)}
                />
                <TableHead className="sticky top-10 z-20 bg-background" />
                <TableHead className="sticky top-10 z-20 bg-background" />
                <TableHead className="sticky top-10 z-20 bg-background" />
                <FilterHeadCell label={tList("remark")} value={filters.remark} onChange={(value) => setFilter("remark", value)} />
              </TableRow>
            </TableHeader>
            <TableBody>
              {shown.length === 0 && (
                <TableRow>
                  <TableCell colSpan={8} className="py-8 text-center text-muted-foreground">
                    {tList("empty")}
                  </TableCell>
                </TableRow>
              )}
              {shown.map((inventory: KarInventory) => {
                const isOpen = openIds.has(inventory.id);
                return (
                  <Fragment key={inventory.id}>
                    <TableRow className="group">
                      <TableCell className="whitespace-nowrap">
                        <button
                          type="button"
                          className="flex items-center gap-1 underline"
                          aria-expanded={isOpen}
                          onClick={() => toggle(inventory.id)}
                        >
                          {isOpen ? <ChevronDown className="size-4" /> : <ChevronRight className="size-4" />}
                          {formatDateTime(inventory.created_at)}
                        </button>
                      </TableCell>
                      <TableCell className="font-medium">{inventory.kar_nummer}</TableCell>
                      <TableCell>{inventory.team_name ?? ""}</TableCell>
                      <TableCell>{inventory.counted_by_name}</TableCell>
                      <TableCell className="text-right tabular-nums">{inventory.total_expected}</TableCell>
                      <TableCell className="text-right tabular-nums">{inventory.total_counted}</TableCell>
                      <TableCell className="text-right">
                        <DifferenceBadge difference={inventory.total_counted - inventory.total_expected} />
                      </TableCell>
                      <TableCell className="max-w-64 truncate text-muted-foreground" title={inventory.remark ?? undefined}>
                        {inventory.remark ?? ""}
                      </TableCell>
                    </TableRow>
                    {isOpen &&
                      inventory.lines.map((line) => (
                        <TableRow key={`line-${line.id}`} className="bg-muted/30">
                          <TableCell />
                          <TableCell colSpan={3}>
                            {line.product_name}
                            {line.is_extra ? (
                              <Badge variant="secondary" className="ml-2">
                                {tList("extra")}
                              </Badge>
                            ) : null}
                          </TableCell>
                          <TableCell className="text-right tabular-nums">{line.expected}</TableCell>
                          <TableCell className="text-right tabular-nums">{line.counted}</TableCell>
                          <TableCell className="text-right">
                            <DifferenceBadge difference={line.counted - line.expected} />
                          </TableCell>
                          <TableCell />
                        </TableRow>
                      ))}
                    {isOpen && inventory.remark ? (
                      <TableRow className="bg-muted/30">
                        <TableCell />
                        <TableCell colSpan={7} className="whitespace-pre-line text-sm italic text-muted-foreground">
                          {inventory.remark}
                        </TableCell>
                      </TableRow>
                    ) : null}
                  </Fragment>
                );
              })}
            </TableBody>
          </Table>
        </div>
      )}
    </div>
  );
}
