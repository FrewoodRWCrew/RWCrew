"use client";

// The dialog behind the "actions waiting" banner on every TagScan screen:
// lists every scanned line whose action (e.g. "Assignment" → create the
// tag) hasn't been carried out yet, lets the user cancel single lines with
// a reason, and processes all the others in one go — then shows the
// per-line outcome (created / already existed / error) as a persistent log
// inside the same dialog, the same way the Excel import does (see
// tag-import-dialog.tsx), rather than a toast that disappears.

import { useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import { toast } from "sonner";
import { useRouter } from "@/i18n/navigation";
import {
  ApiError,
  cancelTagLineProcessing,
  listPendingTagActions,
  processPendingTagActions,
} from "@/lib/api";
import type { TagLineDataEntry, TagLineProcessRowResult } from "@/lib/types";
import { PROCESS_STATUS_ROW_CLASS } from "@/components/module-1/process-status";
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
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { cn } from "@/lib/utils";

interface PendingActionsDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  /** Called after anything changed, so the banner can re-count. */
  onChanged: () => void;
}

const OUTCOME_BADGE_VARIANT: Record<TagLineProcessRowResult["outcome"], "default" | "secondary" | "destructive"> = {
  created: "default",
  exists: "secondary",
  error: "destructive",
};

export function PendingActionsDialog({ open, onOpenChange, onChanged }: PendingActionsDialogProps) {
  const t = useTranslations("tagscan.pendingActions");
  const router = useRouter();

  const [lines, setLines] = useState<TagLineDataEntry[]>([]);
  // True from the start: the list is fetched as soon as the dialog opens.
  const [isLoading, setIsLoading] = useState(true);
  const [isProcessing, setIsProcessing] = useState(false);
  const [results, setResults] = useState<TagLineProcessRowResult[] | null>(null);
  // The line whose "Cancel" was clicked: shows a reason input in its row.
  const [cancellingLineId, setCancellingLineId] = useState<number | null>(null);
  const [cancelComment, setCancelComment] = useState("");
  const [isCancelSaving, setIsCancelSaving] = useState(false);

  /** Fetch the current waiting list; isLoading is managed by the caller. */
  function fetchLines(): Promise<void> {
    return listPendingTagActions()
      .then(setLines)
      .catch((error: unknown) => {
        const message = error instanceof ApiError ? error.message : t("loadFailed");
        toast.error(message);
      })
      .finally(() => setIsLoading(false));
  }

  // The banner remounts this dialog on every open (key), so state already
  // starts clean; load the waiting list once it's actually open.
  useEffect(() => {
    if (!open) return;
    listPendingTagActions()
      .then(setLines)
      .catch((error: unknown) => {
        toast.error(error instanceof ApiError ? error.message : t("loadFailed"));
      })
      .finally(() => setIsLoading(false));
  }, [open, t]);

  /** After a change: refresh the open screen's server data and the banner. */
  function afterChange() {
    router.refresh();
    onChanged();
  }

  async function handleProcessAll() {
    setIsProcessing(true);
    try {
      const response = await processPendingTagActions();
      setResults(response.results);
      // Lines that failed stay waiting — reload so the list shows them.
      setIsLoading(true);
      await fetchLines();
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
  const existsCount = results?.filter((row) => row.outcome === "exists").length ?? 0;
  const errorCount = results?.filter((row) => row.outcome === "error").length ?? 0;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-5xl">
        <DialogHeader>
          <DialogTitle>{t("dialogTitle")}</DialogTitle>
          <DialogDescription>{t("dialogDescription")}</DialogDescription>
        </DialogHeader>

        {/* The outcome of the last "Process" run, kept on screen until the
            dialog is closed. */}
        {results && (
          <div className="flex flex-col gap-2">
            <p className="text-sm font-bold underline">{t("resultsTitle")}</p>
            <p className="text-sm text-muted-foreground">
              {t("resultsSummary", { created: createdCount, exists: existsCount, errors: errorCount })}
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

        {/* The lines still waiting — orange, like "New" rows everywhere else. */}
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
                    <TableHead className="sticky top-0 z-20 bg-background font-bold underline">{t("columnFile")}</TableHead>
                    <TableHead className="sticky top-0 z-20 bg-background font-bold underline">{t("columnLine")}</TableHead>
                    <TableHead className="sticky top-0 z-20 bg-background font-bold underline">{t("columnEpc")}</TableHead>
                    <TableHead className="sticky top-0 z-20 bg-background font-bold underline">{t("columnAction")}</TableHead>
                    <TableHead className="sticky top-0 z-20 bg-background font-bold underline">{t("columnScanner")}</TableHead>
                    <TableHead className="sticky top-0 z-20 bg-background font-bold underline">{t("columnComment")}</TableHead>
                    <TableHead className="sticky top-0 right-0 z-30 bg-background text-right font-bold underline">
                      {t("columnActions")}
                    </TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {lines.map((line) => (
                    <TableRow key={line.id} className={cn("group", PROCESS_STATUS_ROW_CLASS[line.process_status])}>
                      <TableCell>{line.header_filename}</TableCell>
                      <TableCell>{line.line_number}</TableCell>
                      <TableCell className="font-medium">{line.epc}</TableCell>
                      <TableCell>{line.action}</TableCell>
                      <TableCell>{line.scanner_name ?? line.scanner}</TableCell>
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
                </TableBody>
              </Table>
            </div>
          )}
        </div>

        <DialogFooter>
          <Button onClick={handleProcessAll} disabled={isProcessing || isLoading || lines.length === 0}>
            {isProcessing ? t("processing") : t("processAllButton", { count: lines.length })}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
