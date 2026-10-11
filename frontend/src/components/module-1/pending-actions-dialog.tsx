"use client";

// The dialog behind the "actions waiting" banner on every TagScan screen:
// lists every scanned line whose action (e.g. "Assignment" → create the
// tag) hasn't been carried out yet, grouped per scanned file. Every file
// needs a product before it can be processed (a tag must always be assigned
// to a product, and all lines of one CSV are the same product); single
// lines can be cancelled with a reason. After processing, the per-line
// outcome (created / product assigned / already existed / error) stays on
// screen as a log inside the same dialog, the same way the Excel import
// does (see tagscan-data-upload-download.tsx), rather than a toast that disappears.
//
// "Book In" lines are listed too (they're waiting work), but StockMaster
// books them in: their file block links to StockMaster's Inboeken instead
// of asking for a product, and "Process all" leaves them alone.

import { Fragment, useEffect, useMemo, useState } from "react";
import { useTranslations } from "next-intl";
import { toast } from "sonner";
import { Link, useRouter } from "@/i18n/navigation";
import {
  ApiError,
  cancelTagLineProcessing,
  listPendingTagActions,
  listTagscanProducts,
  processPendingTagActions,
} from "@/lib/api";
import type { TagLineDataEntry, TagLineProcessRowResult, TagscanProductOption } from "@/lib/types";
import { PROCESS_STATUS_ROW_CLASS } from "@/components/module-1/process-status";
import { HelpTopicLink } from "@/components/shared/module-help";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { cn } from "@/lib/utils";

interface PendingActionsDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  /** Called after anything changed, so the banner can re-count. */
  onChanged: () => void;
}

/** The CSV action spellings that mean "Book In" (handled by StockMaster),
 * the same list as the backend's BOOK_IN_ACTIONS (line_processing.py). */
const BOOK_IN_ACTIONS = ["book in", "book_in", "bookin", "book-in"];

function isBookInAction(action: string | null): boolean {
  return action !== null && BOOK_IN_ACTIONS.includes(action.trim().toLowerCase());
}

/** StockMaster's Inboeken with the "scans waiting" dialog open. */
const STOCKMASTER_BOOK_IN_HREF = "/modules/module-4/book-in?tagscan=open";

/** All waiting lines of one scanned file (its "Book In" lines form a block of their own). */
interface FileGroup {
  key: string;
  headerId: number;
  /** Book In lines: booked in via StockMaster, not processed here. */
  isBookIn: boolean;
  filename: string;
  /** The CSV's "product / comments" value(s) — hints which product to pick. */
  csvComments: string[];
  lines: TagLineDataEntry[];
}

const OUTCOME_BADGE_VARIANT: Record<TagLineProcessRowResult["outcome"], "default" | "secondary" | "destructive" | "outline"> = {
  created: "default",
  assigned: "outline",
  exists: "secondary",
  error: "destructive",
};

/** Number of columns in the waiting-lines table (for the group rows). */
const WAITING_COLUMN_COUNT = 6;

export function PendingActionsDialog({ open, onOpenChange, onChanged }: PendingActionsDialogProps) {
  const t = useTranslations("tagscan.pendingActions");
  const router = useRouter();

  const [lines, setLines] = useState<TagLineDataEntry[]>([]);
  const [products, setProducts] = useState<TagscanProductOption[]>([]);
  // True from the start: the lists are fetched as soon as the dialog opens.
  const [isLoading, setIsLoading] = useState(true);
  const [isProcessing, setIsProcessing] = useState(false);
  const [results, setResults] = useState<TagLineProcessRowResult[] | null>(null);
  // The product chosen per file (header id → product id).
  const [productByHeader, setProductByHeader] = useState<Record<number, number>>({});
  // The line whose "Cancel" was clicked: shows a reason input in its row.
  const [cancellingLineId, setCancellingLineId] = useState<number | null>(null);
  const [cancelComment, setCancelComment] = useState("");
  const [isCancelSaving, setIsCancelSaving] = useState(false);

  // The banner remounts this dialog on every open (key), so state already
  // starts clean; load the waiting lines and the products once it's open.
  useEffect(() => {
    if (!open) return;
    Promise.all([listPendingTagActions(), listTagscanProducts()])
      .then(([pendingLines, productOptions]) => {
        setLines(pendingLines);
        setProducts(productOptions);
      })
      .catch((error: unknown) => {
        toast.error(error instanceof ApiError ? error.message : t("loadFailed"));
      })
      .finally(() => setIsLoading(false));
  }, [open, t]);

  // Waiting lines grouped per file, in the order they arrive (oldest file
  // first, lines in CSV order — see the backend's list_pending_lines).
  const fileGroups = useMemo<FileGroup[]>(() => {
    const groups = new Map<string, FileGroup>();
    for (const line of lines) {
      const isBookIn = isBookInAction(line.action);
      const key = `${line.header_data_id}-${isBookIn ? "book-in" : "process"}`;
      let group = groups.get(key);
      if (!group) {
        group = {
          key,
          headerId: line.header_data_id,
          isBookIn,
          filename: line.header_filename,
          csvComments: [],
          lines: [],
        };
        groups.set(key, group);
      }
      group.lines.push(line);
      if (line.csv_comment && !group.csvComments.includes(line.csv_comment)) {
        group.csvComments.push(line.csv_comment);
      }
    }
    return [...groups.values()];
  }, [lines]);

  // Only the files processed here; Book In blocks go to StockMaster.
  const processableGroups = fileGroups.filter((group) => !group.isBookIn);
  const processableLineCount = processableGroups.reduce((total, group) => total + group.lines.length, 0);
  const allFilesHaveProduct = processableGroups.every((group) => productByHeader[group.headerId] != null);

  /** After a change: refresh the open screen's server data and the banner. */
  function afterChange() {
    router.refresh();
    onChanged();
  }

  /** Process the given files, each with its chosen product. */
  async function processFiles(headerIds: number[]) {
    const files = headerIds
      .filter((headerId) => productByHeader[headerId] != null)
      .map((headerId) => ({ header_data_id: headerId, product_id: productByHeader[headerId] }));
    if (files.length === 0) {
      toast.error(t("productRequired"));
      return;
    }

    setIsProcessing(true);
    try {
      const response = await processPendingTagActions(files);
      setResults(response.results);
      // Lines that failed stay waiting — reload so the list shows them.
      setLines(await listPendingTagActions());
      afterChange();
    } catch (error) {
      const message = error instanceof ApiError ? error.message : t("processFailed");
      toast.error(message);
    } finally {
      setIsProcessing(false);
    }
  }

  function startCancel(lineId: number) {
    setCancellingLineId(lineId);
    setCancelComment("");
  }

  async function confirmCancel(lineId: number) {
    const comment = cancelComment.trim();
    if (!comment) {
      toast.error(t("commentRequired"));
      return;
    }

    setIsCancelSaving(true);
    try {
      await cancelTagLineProcessing(lineId, comment);
      setLines((current) => current.filter((line) => line.id !== lineId));
      setCancellingLineId(null);
      setCancelComment("");
      toast.success(t("lineCancelled"));
      afterChange();
    } catch (error) {
      const message = error instanceof ApiError ? error.message : t("cancelFailed");
      toast.error(message);
    } finally {
      setIsCancelSaving(false);
    }
  }

  const createdCount = results?.filter((row) => row.outcome === "created").length ?? 0;
  const assignedCount = results?.filter((row) => row.outcome === "assigned").length ?? 0;
  const existsCount = results?.filter((row) => row.outcome === "exists").length ?? 0;
  const errorCount = results?.filter((row) => row.outcome === "error").length ?? 0;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-5xl">
        <DialogHeader>
          <DialogTitle>{t("dialogTitle")}</DialogTitle>
          <DialogDescription>{t("dialogDescription")}</DialogDescription>
          {/* The manual's chapter about processing waiting actions. */}
          <div>
            <HelpTopicLink moduleKey="module-1" topic="pending" />
          </div>
        </DialogHeader>

        {/* The outcome of the last "Process" run, kept on screen until the
            dialog is closed. */}
        {results && (
          <div className="flex flex-col gap-2">
            <p className="text-sm font-bold underline">{t("resultsTitle")}</p>
            <p className="text-sm text-muted-foreground">
              {t("resultsSummary", {
                created: createdCount,
                assigned: assignedCount,
                exists: existsCount,
                errors: errorCount,
              })}
            </p>
            <div className="rounded-md border [&>div]:max-h-60 [&>div]:overflow-y-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="sticky top-0 z-20 bg-background font-bold underline">{t("columnFile")}</TableHead>
                    <TableHead className="sticky top-0 z-20 bg-background font-bold underline">{t("columnLine")}</TableHead>
                    <TableHead className="sticky top-0 z-20 bg-background font-bold underline">{t("columnEpc")}</TableHead>
                    <TableHead className="sticky top-0 z-20 bg-background font-bold underline">{t("columnOutcome")}</TableHead>
                    <TableHead className="sticky top-0 z-20 bg-background font-bold underline">{t("columnDetail")}</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {results.map((row) => (
                    <TableRow key={row.line_id}>
                      <TableCell>{row.header_filename}</TableCell>
                      <TableCell>{row.line_number}</TableCell>
                      <TableCell className="font-medium">{row.epc}</TableCell>
                      <TableCell>
                        <Badge variant={OUTCOME_BADGE_VARIANT[row.outcome]}>{t(`outcome.${row.outcome}`)}</Badge>
                      </TableCell>
                      <TableCell className="text-muted-foreground">{row.detail}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          </div>
        )}

        {/* The lines still waiting, one block per file with its product —
            orange, like "New" rows everywhere else. */}
        <div className="flex flex-col gap-2">
          <p className="text-sm font-bold underline">{t("waitingTitle", { count: lines.length })}</p>
          {isLoading ? (
            <p className="text-sm text-muted-foreground">{t("loading")}</p>
          ) : lines.length === 0 ? (
            <p className="text-sm text-muted-foreground">{t("nothingWaiting")}</p>
          ) : (
            <div className="rounded-md border [&>div]:max-h-[45vh] [&>div]:overflow-y-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="sticky top-0 z-20 bg-background font-bold underline">{t("columnLine")}</TableHead>
                    <TableHead className="sticky top-0 z-20 bg-background font-bold underline">{t("columnEpc")}</TableHead>
                    <TableHead className="sticky top-0 z-20 bg-background font-bold underline">{t("columnAction")}</TableHead>
                    <TableHead className="sticky top-0 z-20 bg-background font-bold underline">{t("columnCsvComment")}</TableHead>
                    <TableHead className="sticky top-0 z-20 bg-background font-bold underline">{t("columnComment")}</TableHead>
                    <TableHead className="sticky top-0 right-0 z-30 bg-background text-right font-bold underline">
                      {t("columnActions")}
                    </TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {fileGroups.map((group) => {
                    const chosenProductId = productByHeader[group.headerId];
                    return (
                      <Fragment key={group.key}>
                        {/* The file's own row: name, line count, its
                            (required) product and a button for just this file. */}
                        <TableRow className="bg-muted/50 hover:bg-muted/50">
                          <TableCell colSpan={WAITING_COLUMN_COUNT}>
                            <div className="flex flex-wrap items-center gap-3">
                              <span className="font-semibold">{group.filename}</span>
                              <span className="text-muted-foreground">
                                {t("fileLineCount", { count: group.lines.length })}
                              </span>
                              {/* What the scanner operator noted for this file. */}
                              {group.csvComments.length > 0 && (
                                <span className="rounded-md border border-orange-500/40 bg-orange-500/10 px-2 py-0.5 text-sm font-medium text-orange-700 dark:text-orange-300">
                                  {t("csvCommentLabel")}: {group.csvComments.join(" / ")}
                                </span>
                              )}
                              {group.isBookIn ? (
                                // Book In: booked in via StockMaster's Inboeken.
                                <div className="ml-auto flex items-center gap-2">
                                  <span className="text-sm text-muted-foreground">{t("bookInInStockMaster")}</span>
                                  <Link
                                    href={STOCKMASTER_BOOK_IN_HREF}
                                    className="text-sm font-semibold underline underline-offset-2"
                                  >
                                    {t("openStockMaster")} →
                                  </Link>
                                </div>
                              ) : (
                                <div className="ml-auto flex items-center gap-2">
                                  <span className="text-sm font-medium">{t("columnProduct")} *</span>
                                  <Select
                                    value={chosenProductId != null ? String(chosenProductId) : null}
                                    onValueChange={(value) =>
                                      setProductByHeader((current) => ({
                                        ...current,
                                        [group.headerId]: Number(value),
                                      }))
                                    }
                                  >
                                    <SelectTrigger
                                      aria-label={t("chooseProduct")}
                                      className={cn("h-8 w-56", chosenProductId == null && "border-orange-500")}
                                    >
                                      <SelectValue>
                                        {(value: string | null) =>
                                          products.find((product) => String(product.id) === value)?.name ??
                                          t("chooseProduct")
                                        }
                                      </SelectValue>
                                    </SelectTrigger>
                                    <SelectContent>
                                      {products.map((product) => (
                                        <SelectItem key={product.id} value={String(product.id)}>
                                          {product.name}
                                        </SelectItem>
                                      ))}
                                    </SelectContent>
                                  </Select>
                                  <Button
                                    size="sm"
                                    disabled={isProcessing || chosenProductId == null}
                                    onClick={() => processFiles([group.headerId])}
                                  >
                                    {t("processFileButton")}
                                  </Button>
                                </div>
                              )}
                            </div>
                          </TableCell>
                        </TableRow>
                        {group.lines.map((line) => (
                          <TableRow key={line.id} className={cn("group", PROCESS_STATUS_ROW_CLASS[line.process_status])}>
                            <TableCell>{line.line_number}</TableCell>
                            <TableCell className="font-medium">{line.epc}</TableCell>
                            <TableCell>{line.action}</TableCell>
                            <TableCell>{line.csv_comment}</TableCell>
                            {/* A previous failed run leaves its error here. */}
                            <TableCell>{line.process_comment}</TableCell>
                            <TableCell className="sticky right-0 z-10 bg-background text-right group-hover:bg-muted/50">
                              {cancellingLineId === line.id ? (
                                <div className="flex items-center justify-end gap-1">
                                  <Input
                                    autoFocus
                                    aria-label={t("cancelReason")}
                                    placeholder={t("cancelReason")}
                                    className="h-8 w-48"
                                    value={cancelComment}
                                    onChange={(event) => setCancelComment(event.target.value)}
                                    onKeyDown={(event) => {
                                      if (event.key === "Enter") void confirmCancel(line.id);
                                    }}
                                  />
                                  <Button
                                    size="sm"
                                    variant="destructive"
                                    disabled={isCancelSaving}
                                    onClick={() => confirmCancel(line.id)}
                                  >
                                    {t("confirmCancel")}
                                  </Button>
                                  <Button size="sm" variant="ghost" onClick={() => setCancellingLineId(null)}>
                                    {t("back")}
                                  </Button>
                                </div>
                              ) : (
                                <Button size="sm" variant="outline" onClick={() => startCancel(line.id)}>
                                  {t("cancelButton")}
                                </Button>
                              )}
                            </TableCell>
                          </TableRow>
                        ))}
                      </Fragment>
                    );
                  })}
                </TableBody>
              </Table>
            </div>
          )}
        </div>

        <DialogFooter className="items-center">
          {/* "Process all" needs a product on every listed file. */}
          {!isLoading && processableLineCount > 0 && !allFilesHaveProduct && (
            <p className="mr-auto text-sm text-orange-600 dark:text-orange-400">{t("productMissingHint")}</p>
          )}
          <Button
            onClick={() => processFiles(processableGroups.map((group) => group.headerId))}
            disabled={isProcessing || isLoading || processableLineCount === 0 || !allFilesHaveProduct}
          >
            {isProcessing ? t("processing") : t("processAllButton", { count: processableLineCount })}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
