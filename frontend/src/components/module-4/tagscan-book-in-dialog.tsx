"use client";

// The dialog behind StockMaster's "scans waiting to be booked in" banner:
// every scanned TagScan file with waiting "Book In" lines, with what it
// would put in Inboeken's basket (product × number of tags) and the lines
// that can't be booked yet (unknown tag, tag without product), which can be
// cancelled with a reason — the same way TagScan's own pending-actions
// dialog works. "Load into Inboeken" opens Inboeken with ?tagscan=<file ids>;
// the booking panel puts the lines in the basket and nothing is booked
// until the person confirms there.

import { Fragment, useEffect, useMemo, useState } from "react";
import { useTranslations } from "next-intl";
import { toast } from "sonner";
import { useRouter } from "@/i18n/navigation";
import {
  ApiError,
  cancelStockMasterTagscanBookInLine,
  getStockMasterStock,
  listStockMasterTagscanBookIn,
} from "@/lib/api";
import { formatDateTime } from "@/lib/date-time";
import type { StockMasterTagscanBookInFile } from "@/lib/types";
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
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { ACTION_PATHS, STOCKMASTER_BASE } from "@/components/module-4/stockmaster-common";

interface TagscanBookInDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  /** Called after anything changed, so the banner can re-count. */
  onChanged: () => void;
}

/** Inboeken with the given scanned files' lines in its basket. */
export function bookInFromScanHref(headerIds: number[]): string {
  return `${STOCKMASTER_BASE}${ACTION_PATHS.book_in}?tagscan=${headerIds.join(",")}`;
}

/** Number of columns in the table (for the file rows). */
const COLUMN_COUNT = 3;

const HEAD_CLASS = "sticky top-0 z-20 bg-background font-bold underline";

export function TagscanBookInDialog({ open, onOpenChange, onChanged }: TagscanBookInDialogProps) {
  const t = useTranslations("stockMaster.tagscanBookIn");
  const tBooking = useTranslations("stockMaster.booking");
  const router = useRouter();

  const [files, setFiles] = useState<StockMasterTagscanBookInFile[]>([]);
  const [productNames, setProductNames] = useState<Map<number, string>>(new Map());
  // True from the start: the lists are fetched as soon as the dialog opens.
  const [isLoading, setIsLoading] = useState(true);
  // The problem line whose "Cancel" was clicked: shows a reason input in its row.
  const [cancellingLineId, setCancellingLineId] = useState<number | null>(null);
  const [cancelComment, setCancelComment] = useState("");
  const [isCancelSaving, setIsCancelSaving] = useState(false);

  // The banner remounts this dialog on every open (key), so state already
  // starts clean; load the waiting scans and the product names once it's open.
  useEffect(() => {
    if (!open) return;
    Promise.all([listStockMasterTagscanBookIn(), getStockMasterStock()])
      .then(([waitingFiles, stock]) => {
        setFiles(waitingFiles);
        setProductNames(new Map(stock.map((product) => [product.product_id, product.name])));
      })
      .catch((error: unknown) => {
        toast.error(error instanceof ApiError ? error.message : t("loadFailed"));
      })
      .finally(() => setIsLoading(false));
  }, [open, t]);

  // Only files with something to book can be loaded into Inboeken.
  const loadableIds = useMemo(
    () => files.filter((file) => file.lines.length > 0).map((file) => file.header_data_id),
    [files],
  );

  /** Open Inboeken with these files' lines in the basket. */
  function loadIntoBookIn(headerIds: number[]) {
    onOpenChange(false);
    router.push(bookInFromScanHref(headerIds));
  }

  /** One problem as readable text ("code|param" → the Excel import's translation). */
  function problemText(detail: string): string {
    const [code, param = ""] = detail.split("|");
    return tBooking.has(`importErrors.${code}`) ? tBooking(`importErrors.${code}`, { p1: param }) : detail;
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
      await cancelStockMasterTagscanBookInLine(lineId, comment);
      // Drop the line, and a file that has nothing left at all.
      setFiles((current) =>
        current
          .map((file) => ({
            ...file,
            problems: file.problems.filter((problem) => problem.line_id !== lineId),
          }))
          .filter((file) => file.lines.length > 0 || file.problems.length > 0),
      );
      setCancellingLineId(null);
      setCancelComment("");
      toast.success(t("lineCancelled"));
      onChanged();
    } catch (error) {
      toast.error(error instanceof ApiError ? error.message : t("cancelFailed"));
    } finally {
      setIsCancelSaving(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-4xl">
        <DialogHeader>
          <DialogTitle>{t("dialogTitle")}</DialogTitle>
          <DialogDescription>{t("dialogDescription")}</DialogDescription>
        </DialogHeader>

        {isLoading ? (
          <p className="text-sm text-muted-foreground">{t("loading")}</p>
        ) : files.length === 0 ? (
          <p className="text-sm text-muted-foreground">{t("nothingWaiting")}</p>
        ) : (
          <div className="rounded-md border [&>div]:max-h-[55vh] [&>div]:overflow-y-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className={HEAD_CLASS}>{t("columnProduct")}</TableHead>
                  <TableHead className={`${HEAD_CLASS} text-right`}>{t("columnQuantity")}</TableHead>
                  <TableHead className={`${HEAD_CLASS} right-0 z-30 text-right`}>{t("columnActions")}</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {files.map((file) => (
                  <Fragment key={file.header_data_id}>
                    {/* The file's own row: name, scan time and its load button. */}
                    <TableRow className="bg-muted/50 hover:bg-muted/50">
                      <TableCell colSpan={COLUMN_COUNT}>
                        <div className="flex flex-wrap items-center gap-3">
                          <span className="font-semibold">{file.filename}</span>
                          <span className="text-muted-foreground">
                            {t("scannedAt", {
                              date: formatDateTime(file.scanned_at),
                            })}
                          </span>
                          <Button
                            size="sm"
                            className="ml-auto"
                            disabled={file.lines.length === 0}
                            onClick={() => loadIntoBookIn([file.header_data_id])}
                          >
                            {t("loadFile")}
                          </Button>
                        </div>
                      </TableCell>
                    </TableRow>

                    {/* What goes into the basket. */}
                    {file.lines.length === 0 ? (
                      <TableRow>
                        <TableCell colSpan={COLUMN_COUNT} className="text-muted-foreground">
                          {t("noBookableLines")}
                        </TableCell>
                      </TableRow>
                    ) : (
                      file.lines.map((line) => (
                        <TableRow key={`${file.header_data_id}-${line.product_id}`} className="group">
                          <TableCell>{productNames.get(line.product_id) ?? `#${line.product_id}`}</TableCell>
                          <TableCell className="text-right font-medium">{line.quantity}</TableCell>
                          <TableCell className="sticky right-0 z-10 bg-background group-hover:bg-muted/50" />
                        </TableRow>
                      ))
                    )}

                    {/* Lines that can't be booked yet — orange, like waiting rows elsewhere. */}
                    {file.problems.length > 0 && (
                      <TableRow className="hover:bg-transparent">
                        <TableCell colSpan={COLUMN_COUNT} className="pt-3 text-sm font-bold underline">
                          {t("problemsTitle", { count: file.problems.length })}
                        </TableCell>
                      </TableRow>
                    )}
                    {file.problems.map((problem) => (
                      <TableRow key={problem.line_id} className="group bg-orange-500/10 hover:bg-orange-500/15">
                        <TableCell colSpan={2} className="text-orange-700 dark:text-orange-300">
                          {tBooking("scanErrorRow", {
                            file: file.filename,
                            row: problem.line_number,
                            message: problemText(problem.detail),
                          })}
                        </TableCell>
                        <TableCell className="sticky right-0 z-10 bg-background text-right group-hover:bg-muted/50">
                          {cancellingLineId === problem.line_id ? (
                            <div className="flex items-center justify-end gap-1">
                              <Input
                                autoFocus
                                aria-label={t("cancelReason")}
                                placeholder={t("cancelReason")}
                                className="h-8 w-48"
                                value={cancelComment}
                                onChange={(event) => setCancelComment(event.target.value)}
                                onKeyDown={(event) => {
                                  if (event.key === "Enter") void confirmCancel(problem.line_id);
                                }}
                              />
                              <Button
                                size="sm"
                                variant="destructive"
                                disabled={isCancelSaving}
                                onClick={() => confirmCancel(problem.line_id)}
                              >
                                {t("confirmCancel")}
                              </Button>
                              <Button size="sm" variant="ghost" onClick={() => setCancellingLineId(null)}>
                                {t("back")}
                              </Button>
                            </div>
                          ) : (
                            <Button size="sm" variant="outline" onClick={() => startCancel(problem.line_id)}>
                              {t("cancelButton")}
                            </Button>
                          )}
                        </TableCell>
                      </TableRow>
                    ))}
                  </Fragment>
                ))}
              </TableBody>
            </Table>
          </div>
        )}

        <DialogFooter>
          <Button onClick={() => loadIntoBookIn(loadableIds)} disabled={isLoading || loadableIds.length === 0}>
            {t("loadAll", { count: loadableIds.length })}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
