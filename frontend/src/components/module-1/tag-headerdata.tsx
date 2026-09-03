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

import { useMemo, useState } from "react";
import { FileText, Trash2 } from "lucide-react";
import { useLocale, useTranslations } from "next-intl";
import { toast } from "sonner";
import { ApiError, deleteTagHeaderData, scanTagHeaderData } from "@/lib/api";
import { API_BASE_URL } from "@/lib/config";
import type { TagHeaderDataEntry, TagHeaderDataScanFileResult } from "@/lib/types";
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
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { cn } from "@/lib/utils";

interface TagHeaderDataProps {
  initialEntries: TagHeaderDataEntry[];
}

/** Plain string slicing instead of toLocaleString(): that depends on the
 * runtime's default locale/timezone, which differs between the server
 * (during SSR) and the browser (during hydration) — causing a hydration
 * mismatch. Slicing the already-ISO string is deterministic everywhere.
 */
function formatDateTime(isoDateTime: string): string {
  return isoDateTime.slice(0, 16).replace("T", " ");
}

function textMatches(fieldValue: string, filterValue: string): boolean {
  if (!filterValue) return true;
  return fieldValue.toLowerCase().includes(filterValue.toLowerCase());
}

export function TagHeaderData({ initialEntries }: TagHeaderDataProps) {
  const t = useTranslations("tagscan.tagHeaderdata");
  const locale = useLocale();

  const [entries, setEntries] = useState(initialEntries);
  const [isScanning, setIsScanning] = useState(false);
  const [scanLog, setScanLog] = useState<TagHeaderDataScanFileResult[] | null>(null);
  const [filenameFilter, setFilenameFilter] = useState("");
  const [createdAtFilter, setCreatedAtFilter] = useState("");
  const [lineCountFilter, setLineCountFilter] = useState("");
  const [scannerNameFilter, setScannerNameFilter] = useState("");
  const [scannerLocationFilter, setScannerLocationFilter] = useState("");
  const [scannerTechnologyFilter, setScannerTechnologyFilter] = useState("");

  const filteredEntries = useMemo(() => {
    return entries.filter((entry) => {
      if (!textMatches(entry.filename, filenameFilter)) return false;
      if (!textMatches(formatDateTime(entry.created_at), createdAtFilter)) return false;
      if (!textMatches(String(entry.line_count), lineCountFilter)) return false;
      if (!textMatches(entry.scanner_name ?? "", scannerNameFilter)) return false;
      if (!textMatches(entry.scanner_location ?? "", scannerLocationFilter)) return false;
      if (!textMatches(entry.scanner_technology ?? "", scannerTechnologyFilter)) return false;
      return true;
    });
  }, [
    entries,
    filenameFilter,
    createdAtFilter,
    lineCountFilter,
    scannerNameFilter,
    scannerLocationFilter,
    scannerTechnologyFilter,
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

      <div className="overflow-x-auto rounded-md border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="font-bold underline">{t("columnFilename")}</TableHead>
              <TableHead className="font-bold underline">{t("columnCreatedAt")}</TableHead>
              <TableHead className="text-right font-bold underline">{t("columnLineCount")}</TableHead>
              <TableHead className="font-bold underline">{t("columnScannerName")}</TableHead>
              <TableHead className="font-bold underline">{t("columnScannerLocation")}</TableHead>
              <TableHead className="font-bold underline">{t("columnScannerTechnology")}</TableHead>
              <TableHead className="text-right font-bold underline">{t("columnActions")}</TableHead>
            </TableRow>
            {/* The filter row: each input sits directly under the column it filters. */}
            <TableRow>
              <TableHead>
                <Input
                  aria-label={t("filterFilename")}
                  placeholder={t("filterFilename")}
                  className="h-8 w-full min-w-32 font-normal"
                  value={filenameFilter}
                  onChange={(event) => setFilenameFilter(event.target.value)}
                />
              </TableHead>
              <TableHead>
                <Input
                  aria-label={t("filterCreatedAt")}
                  placeholder={t("filterCreatedAt")}
                  className="h-8 w-full min-w-32 font-normal"
                  value={createdAtFilter}
                  onChange={(event) => setCreatedAtFilter(event.target.value)}
                />
              </TableHead>
              <TableHead>
                <Input
                  aria-label={t("filterLineCount")}
                  placeholder={t("filterLineCount")}
                  className="h-8 w-full min-w-24 font-normal"
                  value={lineCountFilter}
                  onChange={(event) => setLineCountFilter(event.target.value)}
                />
              </TableHead>
              <TableHead>
                <Input
                  aria-label={t("filterScannerName")}
                  placeholder={t("filterScannerName")}
                  className="h-8 w-full min-w-32 font-normal"
                  value={scannerNameFilter}
                  onChange={(event) => setScannerNameFilter(event.target.value)}
                />
              </TableHead>
              <TableHead>
                <Input
                  aria-label={t("filterScannerLocation")}
                  placeholder={t("filterScannerLocation")}
                  className="h-8 w-full min-w-32 font-normal"
                  value={scannerLocationFilter}
                  onChange={(event) => setScannerLocationFilter(event.target.value)}
                />
              </TableHead>
              <TableHead>
                <Input
                  aria-label={t("filterScannerTechnology")}
                  placeholder={t("filterScannerTechnology")}
                  className="h-8 w-full min-w-32 font-normal"
                  value={scannerTechnologyFilter}
                  onChange={(event) => setScannerTechnologyFilter(event.target.value)}
                />
              </TableHead>
              <TableHead />
            </TableRow>
          </TableHeader>
          <TableBody>
            {filteredEntries.map((entry) => (
              <TableRow key={entry.id}>
                <TableCell className="font-medium">
                  <Link
                    href={`/modules/module-1/tag-linedata?filename=${encodeURIComponent(entry.filename)}`}
                    className="text-primary underline-offset-4 hover:underline"
                  >
                    {entry.filename}
                  </Link>
                </TableCell>
                <TableCell className="text-muted-foreground">{formatDateTime(entry.created_at)}</TableCell>
                <TableCell className="text-right text-muted-foreground">{entry.line_count}</TableCell>
                <TableCell className="text-muted-foreground">{entry.scanner_name}</TableCell>
                <TableCell className="text-muted-foreground">{entry.scanner_location}</TableCell>
                <TableCell className="text-muted-foreground">{entry.scanner_technology}</TableCell>
                <TableCell className="text-right">
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
      toast.success(t("entryDeleted"));
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
            {t("deleteConfirmDescription", { filename: entry.filename })}
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
