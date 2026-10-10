"use client";

// TagScan's "Tag Headerdata" screen: a "Scan" button that reads every
// CSV file currently sitting in the "Unreaded Tags" intake folder, logs
// each new one (filename plus line count plus timestamp), and moves it
// into "Readed Tags" so it's never re-processed — see
// app/modules/module_1/tag_header_data.py for the actual scan logic.
//
// A file that can't be loaded (already logged, or an OS-level failure)
// is never silently dropped: every scan's full per-file outcome is kept
// on screen in the "Scan Log" panel below the table, not just flashed as
// a toast, so a duplicate/error is still visible after the fact.
//
// Each row is coloured by the file's processing status (orange = its lines'
// actions are still waiting, green = loaded, red = cancelled) — see
// process-status.ts.

import { useMemo, useState } from "react";
import { FileText, Trash2 } from "lucide-react";
import { useLocale, useTranslations } from "next-intl";
import { toast } from "sonner";
import { ApiError, deleteTagHeaderData, scanTagHeaderData } from "@/lib/api";
import { API_BASE_URL } from "@/lib/config";
import type { TagHeaderDataEntry, TagHeaderDataScanFileResult } from "@/lib/types";
import {
  PROCESS_STATUS_BADGE_CLASS,
  PROCESS_STATUS_ROW_CLASS,
  PROCESS_STATUS_VALUES,
} from "@/components/module-1/process-status";
import { Link } from "@/i18n/navigation";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { formatDateTime } from "@/lib/date-time";
import { cn } from "@/lib/utils";
import { PENDING_ACTIONS_CHANGED_EVENT } from "@/components/module-1/pending-actions-banner";

interface TagHeaderDataProps {
  initialEntries: TagHeaderDataEntry[];
}

const ALL_VALUE = "all";

function textMatches(fieldValue: string, filterValue: string): boolean {
  if (!filterValue) return true;
  return fieldValue.toLowerCase().includes(filterValue.toLowerCase());
}

export function TagHeaderData({ initialEntries }: TagHeaderDataProps) {
  const t = useTranslations("tagscan.tagHeaderdata");
  const tProcess = useTranslations("tagscan.processStatus");
  const locale = useLocale();

  const [entries, setEntries] = useState(initialEntries);

  // The waiting-actions dialog (banner above every TagScan screen) calls
  // router.refresh() after processing/cancelling, which brings fresh
  // initialEntries from the server — take them over when they change.
  const [previousInitialEntries, setPreviousInitialEntries] = useState(initialEntries);
  if (initialEntries !== previousInitialEntries) {
    setPreviousInitialEntries(initialEntries);
    setEntries(initialEntries);
  }
  const [isScanning, setIsScanning] = useState(false);
  const [scanLog, setScanLog] = useState<TagHeaderDataScanFileResult[] | null>(null);
  const [filenameFilter, setFilenameFilter] = useState("");
  const [createdAtFilter, setCreatedAtFilter] = useState("");
  const [lineCountFilter, setLineCountFilter] = useState("");
  const [scannerNameFilter, setScannerNameFilter] = useState("");
  // The scanner's Type: which activity (module) the file is for.
  const [scannerTypeFilter, setScannerTypeFilter] = useState("");
  const [scannerLocationFilter, setScannerLocationFilter] = useState("");
  const [scannerTechnologyFilter, setScannerTechnologyFilter] = useState("");
  const [modeFilter, setModeFilter] = useState("");
  const [actionFilter, setActionFilter] = useState("");
  const [processStatusFilter, setProcessStatusFilter] = useState(ALL_VALUE);
  const [processCommentFilter, setProcessCommentFilter] = useState("");

  const filteredEntries = useMemo(() => {
    const visible = entries.filter((entry) => {
      if (!textMatches(entry.filename, filenameFilter)) return false;
      if (!textMatches(formatDateTime(entry.created_at), createdAtFilter)) return false;
      if (!textMatches(String(entry.line_count), lineCountFilter)) return false;
      if (!textMatches(entry.scanner_name ?? "", scannerNameFilter)) return false;
      if (!textMatches(entry.scanner_type ?? "", scannerTypeFilter)) return false;
      if (!textMatches(entry.scanner_location ?? "", scannerLocationFilter)) return false;
      if (!textMatches(entry.scanner_technology ?? "", scannerTechnologyFilter)) return false;
      if (!textMatches(entry.mode ?? "", modeFilter)) return false;
      if (!textMatches(entry.action ?? "", actionFilter)) return false;
      if (processStatusFilter !== ALL_VALUE && entry.process_status !== processStatusFilter) return false;
      if (!textMatches(entry.process_comment ?? "", processCommentFilter)) return false;
      return true;
    });
    // Always newest first by "Registered on" (id breaks a tie), whatever
    // order the list arrived in — also right after a Scan or a delete.
    return visible.sort(
      (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime() || b.id - a.id,
    );
  }, [
    entries,
    filenameFilter,
    createdAtFilter,
    lineCountFilter,
    scannerNameFilter,
    scannerTypeFilter,
    scannerLocationFilter,
    scannerTechnologyFilter,
    modeFilter,
    actionFilter,
    processStatusFilter,
    processCommentFilter,
  ]);

  function handleDeleted(deletedId: number) {
    setEntries((current) => current.filter((entry) => entry.id !== deletedId));
  }

  async function handleScan() {
    setIsScanning(true);
    try {
      const result = await scanTagHeaderData();
      setEntries(result.entries);
      setScanLog(result.results);
      // New lines may be waiting now: let the banner re-count.
      window.dispatchEvent(new Event(PENDING_ACTIONS_CHANGED_EVENT));

      const logged = result.results.filter((r) => r.outcome === "logged").length;
      const skipped = result.results.filter((r) => r.outcome === "skipped_duplicate").length;
      const errored = result.results.filter((r) => r.outcome === "error").length;
      toast.success(t("scanSummary", { logged, skipped, errored }));
    } catch (error) {
      const message = error instanceof ApiError ? error.message : t("scanFailed");
      toast.error(message);
    } finally {
      setIsScanning(false);
    }
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight underline">{t("title")}</h1>
          <p className="text-muted-foreground">{t("description")}</p>
        </div>
        <Button onClick={handleScan} disabled={isScanning}>
          {isScanning ? t("scanning") : t("scanButton")}
        </Button>
      </div>

      {scanLog !== null && (
        <div className="rounded-md border">
          <div className="border-b bg-muted/50 px-3 py-2 text-sm font-bold underline">{t("scanLogTitle")}</div>
          {scanLog.length === 0 ? (
            <p className="px-3 py-2 text-sm text-muted-foreground">{t("scanLogEmpty")}</p>
          ) : (
            <ul className="divide-y">
              {scanLog.map((result, index) => (
                <li key={`${result.filename}-${index}`} className="flex flex-wrap items-baseline gap-2 px-3 py-2 text-sm">
                  <span className="font-medium">{result.filename}</span>
                  <span
                    className={cn(
                      "font-semibold",
                      result.outcome === "logged" && "text-green-600 dark:text-green-500",
                      result.outcome === "skipped_duplicate" && "text-amber-600 dark:text-amber-500",
                      result.outcome === "error" && "text-destructive",
                    )}
                  >
                    {t(`outcome.${result.outcome}`)}
                  </span>
                  {result.detail && <span className="text-muted-foreground">— {result.detail}</span>}
                </li>
              ))}
            </ul>
          )}
        </div>
      )}

      <div className="rounded-md border [&>div]:max-h-[65vh] [&>div]:overflow-y-auto">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="sticky top-0 z-20 bg-background font-bold underline">{t("columnProcessStatus")}</TableHead>
              <TableHead className="sticky top-0 z-20 bg-background font-bold underline">{t("columnScannerType")}</TableHead>
              <TableHead className="sticky top-0 z-20 bg-background font-bold underline">{t("columnAction")}</TableHead>
              <TableHead className="sticky top-0 z-20 bg-background font-bold underline">{t("columnFilename")}</TableHead>
              <TableHead className="sticky top-0 z-20 bg-background font-bold underline">{t("columnProcessComment")}</TableHead>
              <TableHead className="sticky top-0 z-20 bg-background font-bold underline">{t("columnCreatedAt")}</TableHead>
              <TableHead className="sticky top-0 z-20 bg-background text-right font-bold underline">{t("columnLineCount")}</TableHead>
              <TableHead className="sticky top-0 z-20 bg-background font-bold underline">{t("columnScannerName")}</TableHead>
              <TableHead className="sticky top-0 z-20 bg-background font-bold underline">{t("columnScannerLocation")}</TableHead>
              <TableHead className="sticky top-0 z-20 bg-background font-bold underline">{t("columnScannerTechnology")}</TableHead>
              <TableHead className="sticky top-0 z-20 bg-background font-bold underline">{t("columnMode")}</TableHead>
              <TableHead className="sticky top-0 right-0 z-30 bg-background text-right font-bold underline">
                {t("columnActions")}
              </TableHead>
            </TableRow>
            {/* The filter row: each input sits directly under the column it filters. */}
            <TableRow>
              <TableHead className="sticky top-10 z-20 bg-background">
                <Select
                  value={processStatusFilter}
                  onValueChange={(value) => setProcessStatusFilter(value ?? ALL_VALUE)}
                >
                  <SelectTrigger aria-label={t("filterProcessStatus")} className="h-8 w-full min-w-28 font-normal">
                    <SelectValue>
                      {(value: string | null) =>
                        value && value !== ALL_VALUE ? tProcess(value) : t("allProcessStatuses")
                      }
                    </SelectValue>
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value={ALL_VALUE}>{t("allProcessStatuses")}</SelectItem>
                    {PROCESS_STATUS_VALUES.map((statusValue) => (
                      <SelectItem key={statusValue} value={statusValue}>
                        {tProcess(statusValue)}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </TableHead>
              <TableHead className="sticky top-10 z-20 bg-background">
                <Input
                  aria-label={t("filterScannerType")}
                  placeholder={t("filterScannerType")}
                  className="h-8 w-full min-w-32 font-normal"
                  value={scannerTypeFilter}
                  onChange={(event) => setScannerTypeFilter(event.target.value)}
                />
              </TableHead>
              <TableHead className="sticky top-10 z-20 bg-background">
                <Input
                  aria-label={t("filterAction")}
                  placeholder={t("filterAction")}
                  className="h-8 w-full min-w-28 font-normal"
                  value={actionFilter}
                  onChange={(event) => setActionFilter(event.target.value)}
                />
              </TableHead>
              <TableHead className="sticky top-10 z-20 bg-background">
                <Input
                  aria-label={t("filterFilename")}
                  placeholder={t("filterFilename")}
                  className="h-8 w-full min-w-32 font-normal"
                  value={filenameFilter}
                  onChange={(event) => setFilenameFilter(event.target.value)}
                />
              </TableHead>
              <TableHead className="sticky top-10 z-20 bg-background">
                <Input
                  aria-label={t("filterProcessComment")}
                  placeholder={t("filterProcessComment")}
                  className="h-8 w-full min-w-32 font-normal"
                  value={processCommentFilter}
                  onChange={(event) => setProcessCommentFilter(event.target.value)}
                />
              </TableHead>
              <TableHead className="sticky top-10 z-20 bg-background">
                <Input
                  aria-label={t("filterCreatedAt")}
                  placeholder={t("filterCreatedAt")}
                  className="h-8 w-full min-w-32 font-normal"
                  value={createdAtFilter}
                  onChange={(event) => setCreatedAtFilter(event.target.value)}
                />
              </TableHead>
              <TableHead className="sticky top-10 z-20 bg-background">
                <Input
                  aria-label={t("filterLineCount")}
                  placeholder={t("filterLineCount")}
                  className="h-8 w-full min-w-24 font-normal"
                  value={lineCountFilter}
                  onChange={(event) => setLineCountFilter(event.target.value)}
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
                  aria-label={t("filterMode")}
                  placeholder={t("filterMode")}
                  className="h-8 w-full min-w-28 font-normal"
                  value={modeFilter}
                  onChange={(event) => setModeFilter(event.target.value)}
                />
              </TableHead>
              <TableHead className="sticky top-10 right-0 z-30 bg-background" />
            </TableRow>
          </TableHeader>
          <TableBody>
            {filteredEntries.map((entry) => (
              // Whole-row colour by processing status; the cells inherit it.
              <TableRow key={entry.id} className={cn("group", PROCESS_STATUS_ROW_CLASS[entry.process_status])}>
                <TableCell>
                  <Badge variant="outline" className={PROCESS_STATUS_BADGE_CLASS[entry.process_status]}>
                    {tProcess(entry.process_status)}
                  </Badge>
                </TableCell>
                <TableCell>{entry.scanner_type}</TableCell>
                <TableCell>{entry.action}</TableCell>
                <TableCell className="font-medium">
                  <Link
                    href={`/modules/module-1/tag-linedata?filename=${encodeURIComponent(entry.filename)}`}
                    className="underline underline-offset-4"
                  >
                    {entry.filename}
                  </Link>
                </TableCell>
                <TableCell>{entry.process_comment}</TableCell>
                <TableCell>{formatDateTime(entry.created_at)}</TableCell>
                <TableCell className="text-right">{entry.line_count}</TableCell>
                <TableCell>{entry.scanner_name}</TableCell>
                <TableCell>{entry.scanner_location}</TableCell>
                <TableCell>{entry.scanner_technology}</TableCell>
                <TableCell>{entry.mode}</TableCell>
                <TableCell className="sticky right-0 z-10 bg-background text-right group-hover:bg-muted/50">
                  <div className="flex justify-end gap-1">
                    <a
                      href={`${API_BASE_URL}/api/modules/module-1/header-data/${entry.id}/pdf?locale=${locale}`}
                      aria-label={t("downloadPdf")}
                      title={t("downloadPdf")}
                      className={cn(
                        "inline-flex size-9 items-center justify-center rounded-md text-muted-foreground transition-colors hover:bg-accent hover:text-accent-foreground",
                      )}
                    >
                      <FileText className="size-4" />
                    </a>
                    <DeleteHeaderDataAlertDialog entry={entry} onDeleted={handleDeleted} />
                  </div>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}

interface DeleteHeaderDataAlertDialogProps {
  entry: TagHeaderDataEntry;
  onDeleted: (id: number) => void;
}

function DeleteHeaderDataAlertDialog({ entry, onDeleted }: DeleteHeaderDataAlertDialogProps) {
  const t = useTranslations("tagscan.tagHeaderdata");
  const tCommon = useTranslations("common");
  const [isOpen, setIsOpen] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);

  async function handleConfirmDelete() {
    setIsDeleting(true);
    try {
      await deleteTagHeaderData(entry.id);
      // The header's lines in Tag Linedata are deleted with it.
      toast.success(t("entryDeleted", { count: entry.line_count }));
      onDeleted(entry.id);
      setIsOpen(false);
    } catch (error) {
      const message = error instanceof ApiError ? error.message : t("deleteFailed");
      toast.error(message);
    } finally {
      setIsDeleting(false);
    }
  }

  return (
    <AlertDialog open={isOpen} onOpenChange={setIsOpen}>
      <AlertDialogTrigger
        render={
          <Button variant="ghost" size="icon" aria-label={t("delete")} title={t("delete")}>
            <Trash2 className="size-4 text-destructive" />
          </Button>
        }
      />
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>{t("deleteConfirmTitle")}</AlertDialogTitle>
          <AlertDialogDescription>
            {t("deleteConfirmDescription", { filename: entry.filename, count: entry.line_count })}
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel>{tCommon("cancel")}</AlertDialogCancel>
          <AlertDialogAction variant="destructive" disabled={isDeleting} onClick={handleConfirmDelete}>
            {t("delete")}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}
