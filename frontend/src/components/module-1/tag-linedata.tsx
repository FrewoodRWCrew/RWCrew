"use client";

// TagScan's "Tag Linedata" screen: every CSV data line a Tag Headerdata
// scan has produced, enriched with a snapshot of its matched
// TagManagement tag (if any) — see app/modules/module_1/tag_header_data.py
// for how a line's EPC gets matched and snapshotted at scan time.
//
// A line's status is "converted" or "no_match" automatically at scan
// time; "cancelled" is the one thing this screen itself can set, via the
// Cancel action below (relies on the backend to 403 if the user lacks
// edit permission — same pattern as every other action button in this
// codebase, e.g. tag-management.tsx's Edit/Delete).

import { Fragment, useMemo, useState } from "react";
import { ArrowDown, ArrowUp, ArrowUpDown, Layers } from "lucide-react";
import { useTranslations } from "next-intl";
import { useSearchParams } from "next/navigation";
import { toast } from "sonner";
import { ApiError, cancelTagLineData, syncTagLineData } from "@/lib/api";
import type { TagLineDataEntry, TagLineStatus } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { cn } from "@/lib/utils";

interface TagLineDataProps {
  initialEntries: TagLineDataEntry[];
}

const STATUS_VALUES: TagLineStatus[] = ["converted", "no_match", "cancelled"];
const ALL_VALUE = "all";

/** Every column a user can click to sort by — matches the corresponding
 * TagLineDataEntry field name directly, so the comparator can index into
 * an entry with it without a separate lookup table.
 */
type SortableColumn =
  | "header_filename"
  | "line_number"
  | "scanner"
  | "scanner_name"
  | "scanner_location"
  | "scanner_technology"
  | "epc"
  | "rssi"
  | "antenna"
  | "count"
  | "last_seen"
  | "assigned_product_name"
  | "assigned_serial_number"
  | "manufacturer"
  | "batch_number"
  | "status";

type SortDirection = "asc" | "desc";

/** The grouped view is built from these — either one ungrouped line
 * (status "no_match"/"cancelled", or a "converted" line whose tag has no
 * assigned product) shown exactly as in the flat table, or one (filename,
 * product) cluster followed by its own subtotal row.
 */
type DisplayBlock =
  | { type: "line"; entry: TagLineDataEntry }
  | { type: "group"; key: string; filename: string; product: string; entries: TagLineDataEntry[] };

function textMatches(fieldValue: string | number | null, filterValue: string): boolean {
  if (!filterValue) return true;
  return String(fieldValue ?? "").toLowerCase().includes(filterValue.toLowerCase());
}

interface SortableHeaderProps {
  label: string;
  column: SortableColumn;
  activeColumn: SortableColumn | null;
  direction: SortDirection;
  onSort: (column: SortableColumn) => void;
  /** True while the grouped view is active — sorting and grouping are two
   * different orderings of the same rows, and letting both apply at once
   * would fight each other, so sorting is inert (but still visible,
   * dimmed) until grouping is turned back off.
   */
  disabled?: boolean;
  className?: string;
}

/** A column header that's both the mandatory bold+underlined label AND
 * the click target to sort by that column — an arrow shows the current
 * sort direction on the active column, and a faint neutral icon on every
 * other column hints that it's clickable too.
 */
function SortableHeader({ label, column, activeColumn, direction, onSort, disabled, className }: SortableHeaderProps) {
  const isActive = activeColumn === column && !disabled;
  return (
    <TableHead className={cn("select-none font-bold underline", disabled ? "cursor-default" : "cursor-pointer", className)}>
      <button
        type="button"
        onClick={() => onSort(column)}
        disabled={disabled}
        className="inline-flex w-full items-center gap-1 text-left disabled:cursor-default"
      >
        {label}
        {isActive ? (
          direction === "asc" ? (
            <ArrowUp className="size-3.5" />
          ) : (
            <ArrowDown className="size-3.5" />
          )
        ) : (
          <ArrowUpDown className={cn("size-3.5 text-muted-foreground/50", disabled && "opacity-40")} />
        )}
      </button>
    </TableHead>
  );
}

export function TagLineData({ initialEntries }: TagLineDataProps) {
  const t = useTranslations("tagscan.tagLinedata");
  const searchParams = useSearchParams();

  const [entries, setEntries] = useState(initialEntries);
  const [cancellingId, setCancellingId] = useState<number | null>(null);
  const [isSyncing, setIsSyncing] = useState(false);
  const [groupByProduct, setGroupByProduct] = useState(false);

  // Pre-filled when arriving from a filename link on Tag Headerdata
  // (?filename=...) — every other filter still starts blank as usual.
  const [headerFilenameFilter, setHeaderFilenameFilter] = useState(() => searchParams.get("filename") ?? "");
  const [lineNumberFilter, setLineNumberFilter] = useState("");
  const [scannerFilter, setScannerFilter] = useState("");
  const [scannerNameFilter, setScannerNameFilter] = useState("");
  const [scannerLocationFilter, setScannerLocationFilter] = useState("");
  const [scannerTechnologyFilter, setScannerTechnologyFilter] = useState("");
  const [epcFilter, setEpcFilter] = useState("");
  const [rssiFilter, setRssiFilter] = useState("");
  const [antennaFilter, setAntennaFilter] = useState("");
  const [countFilter, setCountFilter] = useState("");
  const [lastSeenFilter, setLastSeenFilter] = useState("");
  const [productFilter, setProductFilter] = useState("");
  const [serialNumberFilter, setSerialNumberFilter] = useState("");
  const [manufacturerFilter, setManufacturerFilter] = useState("");
  const [batchNumberFilter, setBatchNumberFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState(ALL_VALUE);

  // No column sorted by default: entries arrive from the backend already
  // ordered newest-scanned-file-first with lines in CSV order, which is
  // worth preserving until the user actively asks for something else.
  const [sortColumn, setSortColumn] = useState<SortableColumn | null>(null);
  const [sortDirection, setSortDirection] = useState<SortDirection>("asc");

  function handleSort(column: SortableColumn) {
    if (sortColumn === column) {
      setSortDirection((current) => (current === "asc" ? "desc" : "asc"));
    } else {
      setSortColumn(column);
      setSortDirection("asc");
    }
  }

  const filteredEntries = useMemo(() => {
    return entries.filter((entry) => {
      if (!textMatches(entry.header_filename, headerFilenameFilter)) return false;
      if (!textMatches(entry.line_number, lineNumberFilter)) return false;
      if (!textMatches(entry.scanner, scannerFilter)) return false;
      if (!textMatches(entry.scanner_name, scannerNameFilter)) return false;
      if (!textMatches(entry.scanner_location, scannerLocationFilter)) return false;
      if (!textMatches(entry.scanner_technology, scannerTechnologyFilter)) return false;
      if (!textMatches(entry.epc, epcFilter)) return false;
      if (!textMatches(entry.rssi, rssiFilter)) return false;
      if (!textMatches(entry.antenna, antennaFilter)) return false;
      if (!textMatches(entry.count, countFilter)) return false;
      if (!textMatches(entry.last_seen, lastSeenFilter)) return false;
      if (!textMatches(entry.assigned_product_name, productFilter)) return false;
      if (!textMatches(entry.assigned_serial_number, serialNumberFilter)) return false;
      if (!textMatches(entry.manufacturer, manufacturerFilter)) return false;
      if (!textMatches(entry.batch_number, batchNumberFilter)) return false;
      if (statusFilter !== ALL_VALUE && entry.status !== statusFilter) return false;
      return true;
    });
  }, [
    entries,
    headerFilenameFilter,
    lineNumberFilter,
    scannerFilter,
    scannerNameFilter,
    scannerLocationFilter,
    scannerTechnologyFilter,
    epcFilter,
    rssiFilter,
    antennaFilter,
    countFilter,
    lastSeenFilter,
    productFilter,
    serialNumberFilter,
    manufacturerFilter,
    batchNumberFilter,
    statusFilter,
  ]);

  const sortedEntries = useMemo(() => {
    if (!sortColumn) return filteredEntries;

    const factor = sortDirection === "asc" ? 1 : -1;
    return [...filteredEntries].sort((a, b) => {
      const aValue = a[sortColumn];
      const bValue = b[sortColumn];
      // Missing values always sort last, regardless of direction — a
      // blank cell isn't meaningfully "smaller" or "larger" than a real one.
      if (aValue == null && bValue == null) return 0;
      if (aValue == null) return 1;
      if (bValue == null) return -1;
      if (typeof aValue === "number" && typeof bValue === "number") {
        return (aValue - bValue) * factor;
      }
      return String(aValue).localeCompare(String(bValue)) * factor;
    });
  }, [filteredEntries, sortColumn, sortDirection]);

  // Built from filteredEntries (not sortedEntries): grouping is its own
  // ordering of the currently-filtered rows, applied instead of — not on
  // top of — column sorting (see SortableHeader's `disabled` prop above).
  // A single pass keeps every ungrouped line exactly where it already
  // was, while each (filename, product) group's scattered rows collapse
  // into one contiguous block at the position of their first occurrence —
  // a stable transform, not a full re-sort.
  const groupedBlocks = useMemo<DisplayBlock[]>(() => {
    const blocks: DisplayBlock[] = [];
    const groupsByKey = new Map<string, Extract<DisplayBlock, { type: "group" }>>();

    for (const entry of filteredEntries) {
      // Cancelling a line only flips its status — it keeps whatever
      // product snapshot it had before cancellation — so status must be
      // checked explicitly here too, not just a null product name, or a
      // cancelled-but-previously-converted line would wrongly rejoin its
      // old product's group instead of staying listed on its own.
      if (entry.status === "cancelled" || entry.assigned_product_name == null) {
        blocks.push({ type: "line", entry });
        continue;
      }

      const key = `${entry.header_filename} ${entry.assigned_product_name}`;
      let group = groupsByKey.get(key);
      if (!group) {
        group = { type: "group", key, filename: entry.header_filename, product: entry.assigned_product_name, entries: [] };
        groupsByKey.set(key, group);
        blocks.push(group);
      }
      group.entries.push(entry);
    }

    return blocks;
  }, [filteredEntries]);

  async function handleSync() {
    setIsSyncing(true);
    try {
      const result = await syncTagLineData();
      setEntries(result.entries);
      toast.success(t("syncSummary", { count: result.updated_count }));
    } catch (error) {
      const message = error instanceof ApiError ? error.message : t("syncFailed");
      toast.error(message);
    } finally {
      setIsSyncing(false);
    }
  }

  async function handleCancel(entry: TagLineDataEntry) {
    setCancellingId(entry.id);
    try {
      const updated = await cancelTagLineData(entry.id);
      setEntries((current) => current.map((item) => (item.id === updated.id ? updated : item)));
      toast.success(t("lineCancelled"));
    } catch (error) {
      const message = error instanceof ApiError ? error.message : t("cancelFailed");
      toast.error(message);
    } finally {
      setCancellingId(null);
    }
  }

  function renderEntryRow(entry: TagLineDataEntry) {
    // Whole-row status colour, overriding every cell's default
    // text-muted-foreground below — green/red/yellow so the outcome of a
    // line is readable at a glance without reading the status column
    // itself. Dark-mode variants keep contrast against the dark theme
    // this app defaults to (see next-themes note in CLAUDE.md Gotchas).
    const statusRowClassName = cn(
      "group",
      entry.status === "converted" && "text-green-600 dark:text-green-400",
      entry.status === "no_match" && "text-red-600 dark:text-red-400",
      entry.status === "cancelled" && "text-yellow-600 dark:text-yellow-400",
    );
    return (
      <TableRow key={entry.id} className={statusRowClassName}>
        <TableCell>{t(`status.${entry.status}`)}</TableCell>
        <TableCell className="font-medium">{entry.epc}</TableCell>
        <TableCell>{entry.assigned_product_name}</TableCell>
        <TableCell>{entry.assigned_serial_number}</TableCell>
        <TableCell>{entry.scanner}</TableCell>
        <TableCell>{entry.scanner_name}</TableCell>
        <TableCell>{entry.scanner_location}</TableCell>
        <TableCell>{entry.scanner_technology}</TableCell>
        <TableCell>{entry.last_seen}</TableCell>
        <TableCell>{entry.header_filename}</TableCell>
        <TableCell>{entry.line_number}</TableCell>
        <TableCell>{entry.rssi}</TableCell>
        <TableCell>{entry.antenna}</TableCell>
        <TableCell>{entry.count}</TableCell>
        <TableCell>{entry.manufacturer}</TableCell>
        <TableCell>{entry.batch_number}</TableCell>
        <TableCell className="sticky right-0 z-10 bg-background text-right group-hover:bg-muted/50">
          {entry.status !== "cancelled" && (
            <Button
              variant="outline"
              size="sm"
              disabled={cancellingId === entry.id}
              onClick={() => handleCancel(entry)}
            >
              {t("cancelButton")}
            </Button>
          )}
        </TableCell>
      </TableRow>
    );
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight underline">{t("title")}</h1>
          <p className="text-muted-foreground">{t("description")}</p>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant={groupByProduct ? "default" : "outline"}
            onClick={() => setGroupByProduct((current) => !current)}
          >
            <Layers className="size-4" />
            {t("groupByProductButton")}
          </Button>
          <Button variant="outline" onClick={handleSync} disabled={isSyncing}>
            {isSyncing ? t("syncing") : t("syncButton")}
          </Button>
        </div>
      </div>

      {/* <Table> itself wraps the <table> in its own scrolling div
          (data-slot="table-container", already overflow-x-auto) — bound
          THAT element's height and give it overflow-y too, via the
          [&>div] arbitrary-variant selector, rather than adding another
          wrapping div of our own. Two independent scroll containers
          (ours + Table's) would leave the horizontal scrollbar pinned to
          the bottom of the full, unclipped table — only reachable after
          scrolling our own box all the way down, i.e. still invisible.
          Both header rows are sticky so they (and the filters) stay
          visible while scrolling through the results. */}
      <div className="rounded-md border [&>div]:max-h-[65vh] [&>div]:overflow-y-auto">
        <Table>
          <TableHeader>
            <TableRow>
              <SortableHeader
                label={t("columnStatus")}
                column="status"
                activeColumn={sortColumn}
                direction={sortDirection}
                onSort={handleSort}
                disabled={groupByProduct}
                className="sticky top-0 z-20 bg-background"
              />
              <SortableHeader
                label={t("columnEpc")}
                column="epc"
                activeColumn={sortColumn}
                direction={sortDirection}
                onSort={handleSort}
                disabled={groupByProduct}
                className="sticky top-0 z-20 bg-background"
              />
              <SortableHeader
                label={t("columnProduct")}
                column="assigned_product_name"
                activeColumn={sortColumn}
                direction={sortDirection}
                onSort={handleSort}
                disabled={groupByProduct}
                className="sticky top-0 z-20 bg-background"
              />
              <SortableHeader
                label={t("columnSerialNumber")}
                column="assigned_serial_number"
                activeColumn={sortColumn}
                direction={sortDirection}
                onSort={handleSort}
                disabled={groupByProduct}
                className="sticky top-0 z-20 bg-background"
              />
              <SortableHeader
                label={t("columnScanner")}
                column="scanner"
                activeColumn={sortColumn}
                direction={sortDirection}
                onSort={handleSort}
                disabled={groupByProduct}
                className="sticky top-0 z-20 bg-background"
              />
              <SortableHeader
                label={t("columnScannerName")}
                column="scanner_name"
                activeColumn={sortColumn}
                direction={sortDirection}
                onSort={handleSort}
                disabled={groupByProduct}
                className="sticky top-0 z-20 bg-background"
              />
              <SortableHeader
                label={t("columnScannerLocation")}
                column="scanner_location"
                activeColumn={sortColumn}
                direction={sortDirection}
                onSort={handleSort}
                disabled={groupByProduct}
                className="sticky top-0 z-20 bg-background"
              />
              <SortableHeader
                label={t("columnScannerTechnology")}
                column="scanner_technology"
                activeColumn={sortColumn}
                direction={sortDirection}
                onSort={handleSort}
                disabled={groupByProduct}
                className="sticky top-0 z-20 bg-background"
              />
              <SortableHeader
                label={t("columnLastSeen")}
                column="last_seen"
                activeColumn={sortColumn}
                direction={sortDirection}
                onSort={handleSort}
                disabled={groupByProduct}
                className="sticky top-0 z-20 bg-background"
              />
              <SortableHeader
                label={t("columnHeaderFilename")}
                column="header_filename"
                activeColumn={sortColumn}
                direction={sortDirection}
                onSort={handleSort}
                disabled={groupByProduct}
                className="sticky top-0 z-20 bg-background"
              />
              <SortableHeader
                label={t("columnLineNumber")}
                column="line_number"
                activeColumn={sortColumn}
                direction={sortDirection}
                onSort={handleSort}
                disabled={groupByProduct}
                className="sticky top-0 z-20 bg-background"
              />
              <SortableHeader
                label={t("columnRssi")}
                column="rssi"
                activeColumn={sortColumn}
                direction={sortDirection}
                onSort={handleSort}
                disabled={groupByProduct}
                className="sticky top-0 z-20 bg-background"
              />
              <SortableHeader
                label={t("columnAntenna")}
                column="antenna"
                activeColumn={sortColumn}
                direction={sortDirection}
                onSort={handleSort}
                disabled={groupByProduct}
                className="sticky top-0 z-20 bg-background"
              />
              <SortableHeader
                label={t("columnCount")}
                column="count"
                activeColumn={sortColumn}
                direction={sortDirection}
                onSort={handleSort}
                disabled={groupByProduct}
                className="sticky top-0 z-20 bg-background"
              />
              <SortableHeader
                label={t("columnManufacturer")}
                column="manufacturer"
                activeColumn={sortColumn}
                direction={sortDirection}
                onSort={handleSort}
                disabled={groupByProduct}
                className="sticky top-0 z-20 bg-background"
              />
              <SortableHeader
                label={t("columnBatchNumber")}
                column="batch_number"
                activeColumn={sortColumn}
                direction={sortDirection}
                onSort={handleSort}
                disabled={groupByProduct}
                className="sticky top-0 z-20 bg-background"
              />
              <TableHead className="sticky top-0 right-0 z-30 bg-background text-right font-bold underline">
                {t("columnActions")}
              </TableHead>
            </TableRow>
            {/* The filter row: each control sits directly under the column it filters. */}
            <TableRow>
              <TableHead className="sticky top-10 z-20 bg-background">
                <Select value={statusFilter} onValueChange={(value) => setStatusFilter(value ?? ALL_VALUE)}>
                  <SelectTrigger aria-label={t("filterStatus")} className="h-8 w-full font-normal">
                    <SelectValue>
                      {(value: string | null) =>
                        value && value !== ALL_VALUE ? t(`status.${value}`) : t("allStatuses")
                      }
                    </SelectValue>
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value={ALL_VALUE}>{t("allStatuses")}</SelectItem>
                    {STATUS_VALUES.map((statusValue) => (
                      <SelectItem key={statusValue} value={statusValue}>
                        {t(`status.${statusValue}`)}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </TableHead>
              <TableHead className="sticky top-10 z-20 bg-background">
                <Input
                  aria-label={t("filterEpc")}
                  placeholder={t("filterEpc")}
                  className="h-8 w-full min-w-32 font-normal"
                  value={epcFilter}
                  onChange={(event) => setEpcFilter(event.target.value)}
                />
              </TableHead>
              <TableHead className="sticky top-10 z-20 bg-background">
                <Input
                  aria-label={t("filterProduct")}
                  placeholder={t("filterProduct")}
                  className="h-8 w-full min-w-32 font-normal"
                  value={productFilter}
                  onChange={(event) => setProductFilter(event.target.value)}
                />
              </TableHead>
              <TableHead className="sticky top-10 z-20 bg-background">
                <Input
                  aria-label={t("filterSerialNumber")}
                  placeholder={t("filterSerialNumber")}
                  className="h-8 w-full min-w-32 font-normal"
                  value={serialNumberFilter}
                  onChange={(event) => setSerialNumberFilter(event.target.value)}
                />
              </TableHead>
              <TableHead className="sticky top-10 z-20 bg-background">
                <Input
                  aria-label={t("filterScanner")}
                  placeholder={t("filterScanner")}
                  className="h-8 w-full min-w-24 font-normal"
                  value={scannerFilter}
                  onChange={(event) => setScannerFilter(event.target.value)}
                />
              </TableHead>
              <TableHead className="sticky top-10 z-20 bg-background">
                <Input
                  aria-label={t("filterScannerName")}
                  placeholder={t("filterScannerName")}
                  className="h-8 w-full min-w-32 font-normal"
                  value={scannerNameFilter}
                  onChange={(event) => setScannerNameFilter(event.target.value)}
                />
              </TableHead>
              <TableHead className="sticky top-10 z-20 bg-background">
                <Input
                  aria-label={t("filterScannerLocation")}
                  placeholder={t("filterScannerLocation")}
                  className="h-8 w-full min-w-32 font-normal"
                  value={scannerLocationFilter}
                  onChange={(event) => setScannerLocationFilter(event.target.value)}
                />
              </TableHead>
              <TableHead className="sticky top-10 z-20 bg-background">
                <Input
                  aria-label={t("filterScannerTechnology")}
                  placeholder={t("filterScannerTechnology")}
                  className="h-8 w-full min-w-32 font-normal"
                  value={scannerTechnologyFilter}
                  onChange={(event) => setScannerTechnologyFilter(event.target.value)}
                />
              </TableHead>
              <TableHead className="sticky top-10 z-20 bg-background">
                <Input
                  aria-label={t("filterLastSeen")}
                  placeholder={t("filterLastSeen")}
                  className="h-8 w-full min-w-24 font-normal"
                  value={lastSeenFilter}
                  onChange={(event) => setLastSeenFilter(event.target.value)}
                />
              </TableHead>
              <TableHead className="sticky top-10 z-20 bg-background">
                <Input
                  aria-label={t("filterHeaderFilename")}
                  placeholder={t("filterHeaderFilename")}
                  className="h-8 w-full min-w-32 font-normal"
                  value={headerFilenameFilter}
                  onChange={(event) => setHeaderFilenameFilter(event.target.value)}
                />
              </TableHead>
              <TableHead className="sticky top-10 z-20 bg-background">
                <Input
                  aria-label={t("filterLineNumber")}
                  placeholder={t("filterLineNumber")}
                  className="h-8 w-full min-w-20 font-normal"
                  value={lineNumberFilter}
                  onChange={(event) => setLineNumberFilter(event.target.value)}
                />
              </TableHead>
              <TableHead className="sticky top-10 z-20 bg-background">
                <Input
                  aria-label={t("filterRssi")}
                  placeholder={t("filterRssi")}
                  className="h-8 w-full min-w-16 font-normal"
                  value={rssiFilter}
                  onChange={(event) => setRssiFilter(event.target.value)}
                />
              </TableHead>
              <TableHead className="sticky top-10 z-20 bg-background">
                <Input
                  aria-label={t("filterAntenna")}
                  placeholder={t("filterAntenna")}
                  className="h-8 w-full min-w-16 font-normal"
                  value={antennaFilter}
                  onChange={(event) => setAntennaFilter(event.target.value)}
                />
              </TableHead>
              <TableHead className="sticky top-10 z-20 bg-background">
                <Input
                  aria-label={t("filterCount")}
                  placeholder={t("filterCount")}
                  className="h-8 w-full min-w-16 font-normal"
                  value={countFilter}
                  onChange={(event) => setCountFilter(event.target.value)}
                />
              </TableHead>
              <TableHead className="sticky top-10 z-20 bg-background">
                <Input
                  aria-label={t("filterManufacturer")}
                  placeholder={t("filterManufacturer")}
                  className="h-8 w-full min-w-32 font-normal"
                  value={manufacturerFilter}
                  onChange={(event) => setManufacturerFilter(event.target.value)}
                />
              </TableHead>
              <TableHead className="sticky top-10 z-20 bg-background">
                <Input
                  aria-label={t("filterBatchNumber")}
                  placeholder={t("filterBatchNumber")}
                  className="h-8 w-full min-w-32 font-normal"
                  value={batchNumberFilter}
                  onChange={(event) => setBatchNumberFilter(event.target.value)}
                />
              </TableHead>
              <TableHead className="sticky top-10 right-0 z-30 bg-background" />
            </TableRow>
          </TableHeader>
          <TableBody>
            {groupByProduct
              ? groupedBlocks.map((block) =>
                  block.type === "line" ? (
                    renderEntryRow(block.entry)
                  ) : (
                    <Fragment key={block.key}>
                      {block.entries.map((entry) => renderEntryRow(entry))}
                      <TableRow className="bg-muted/50 hover:bg-muted/50">
                        <TableCell colSpan={17} className="font-semibold">
                          {t("subtotalLabel", {
                            product: block.product,
                            filename: block.filename,
                            count: block.entries.length,
                          })}
                        </TableCell>
                      </TableRow>
                    </Fragment>
                  ),
                )
              : sortedEntries.map((entry) => renderEntryRow(entry))}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}
