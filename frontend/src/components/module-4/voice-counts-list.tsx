"use client";

// StockMaster's "Spraaktellingen": the kars counted by voice on the phone
// (/m/module-4/voice-count), newest first, for the chosen season — date
// (Belgian time), kar, Ophalen/Terugbrengen, pieces, who counted and the
// status. A row opens to show its products with what was said; each count can
// be downloaded as CSV and, while still "new", cancelled ("edit" right).
// Phase 1 only stores the counts: booking them into stock comes later (its
// button will go on this screen).

import { Fragment, useCallback, useEffect, useState } from "react";
import { ChevronDown, ChevronRight, FileDown, XCircle } from "lucide-react";
import { useTranslations } from "next-intl";
import { toast } from "sonner";
import { cancelStockMasterVoiceCount, listStockMasterVoiceCounts, stockMasterVoiceCountCsvUrl } from "@/lib/api";
import { formatDateTime } from "@/lib/date-time";
import type { Season, StockMasterVoiceCount, StockMasterVoiceCountStatus } from "@/lib/types";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { Badge } from "@/components/ui/badge";
import { Button, buttonVariants } from "@/components/ui/button";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { stockErrorMessage } from "@/components/module-4/stockmaster-common";
import { StockMasterSeasonSelect, useStockMasterSeasonId } from "@/components/module-4/stockmaster-season-select";

const HEAD_CLASS = "sticky top-0 z-20 bg-background font-bold underline";

// Badge look per status.
const STATUS_VARIANT: Record<StockMasterVoiceCountStatus, "secondary" | "default" | "destructive"> = {
  new: "secondary",
  booked: "default",
  cancelled: "destructive",
};

interface VoiceCountsListProps {
  seasons: Season[];
  /** "edit" on the voice count screen: may cancel a count. */
  canEdit: boolean;
}

export function VoiceCountsList({ seasons, canEdit }: VoiceCountsListProps) {
  const t = useTranslations("stockMaster");
  const tList = useTranslations("stockMaster.voiceCounts");
  const seasonId = useStockMasterSeasonId(seasons);

  const [counts, setCounts] = useState<StockMasterVoiceCount[] | null>(null);
  // The rows opened to show their products.
  const [openIds, setOpenIds] = useState<Set<number>>(new Set());
  // The count waiting for "really cancel?".
  const [toCancel, setToCancel] = useState<StockMasterVoiceCount | null>(null);

  const load = useCallback(() => {
    if (seasonId === null) return;
    listStockMasterVoiceCounts(seasonId)
      .then(setCounts)
      .catch(() => toast.error(t("errors.loadFailed")));
  }, [seasonId, t]);

  useEffect(load, [load]);

  function toggle(id: number) {
    setOpenIds((current) => {
      const next = new Set(current);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  async function confirmCancel() {
    if (!toCancel) return;
    try {
      await cancelStockMasterVoiceCount(toCancel.id);
      toast.success(tList("cancelled", { kar: toCancel.kar_nummer }));
      load();
    } catch (error) {
      toast.error(stockErrorMessage(t, error));
    } finally {
      setToCancel(null);
    }
  }

  return (
    <div className="flex flex-col gap-4">
      <div>
        <h1 className="text-2xl font-bold tracking-tight underline">{tList("title")}</h1>
        <p className="text-muted-foreground">{tList("description")}</p>
      </div>

      <StockMasterSeasonSelect seasons={seasons} seasonId={seasonId} />

      {counts === null ? (
        <p className="text-sm text-muted-foreground">{t("common.loading")}</p>
      ) : (
        <div className="rounded-md border [&>div]:max-h-[65vh] [&>div]:overflow-y-auto">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className={HEAD_CLASS}>{tList("date")}</TableHead>
                <TableHead className={HEAD_CLASS}>{t("common.kar")}</TableHead>
                <TableHead className={HEAD_CLASS}>{tList("direction")}</TableHead>
                <TableHead className={`${HEAD_CLASS} text-right`}>{tList("lines")}</TableHead>
                <TableHead className={`${HEAD_CLASS} text-right`}>{tList("pieces")}</TableHead>
                <TableHead className={HEAD_CLASS}>{tList("countedBy")}</TableHead>
                <TableHead className={HEAD_CLASS}>{tList("status")}</TableHead>
                <TableHead className="sticky top-0 right-0 z-30 bg-background text-right font-bold underline">
                  {t("common.actions")}
                </TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {counts.length === 0 && (
                <TableRow>
                  <TableCell colSpan={8} className="py-8 text-center text-muted-foreground">
                    {tList("empty")}
                  </TableCell>
                </TableRow>
              )}
              {counts.map((count) => {
                const isOpen = openIds.has(count.id);
                return (
                  <Fragment key={count.id}>
                    <TableRow className="group">
                      <TableCell className="whitespace-nowrap">
                        <button
                          type="button"
                          className="flex items-center gap-1 underline"
                          aria-expanded={isOpen}
                          onClick={() => toggle(count.id)}
                        >
                          {isOpen ? <ChevronDown className="size-4" /> : <ChevronRight className="size-4" />}
                          {formatDateTime(count.created_at)}
                        </button>
                      </TableCell>
                      <TableCell className="font-medium">{count.kar_nummer}</TableCell>
                      <TableCell>{tList(`directions.${count.direction}`)}</TableCell>
                      <TableCell className="text-right tabular-nums">{count.lines.length}</TableCell>
                      <TableCell className="text-right tabular-nums">{count.total_quantity}</TableCell>
                      <TableCell>{count.created_by_name ?? ""}</TableCell>
                      <TableCell>
                        <Badge
                          variant={STATUS_VARIANT[count.status]}
                          title={
                            count.status === "cancelled" && count.cancelled_at
                              ? tList("cancelledBy", {
                                  name: count.cancelled_by_name ?? "",
                                  date: formatDateTime(count.cancelled_at),
                                })
                              : undefined
                          }
                        >
                          {tList(`statuses.${count.status}`)}
                        </Badge>
                      </TableCell>
                      <TableCell className="sticky right-0 z-10 bg-background text-right group-hover:bg-muted/50">
                        <div className="flex justify-end gap-1">
                          <a
                            href={stockMasterVoiceCountCsvUrl(count.id)}
                            aria-label={tList("csv")}
                            title={tList("csv")}
                            className={buttonVariants({ variant: "ghost", size: "icon-sm" })}
                          >
                            <FileDown />
                          </a>
                          {canEdit && count.status === "new" && (
                            <Button
                              variant="ghost"
                              size="icon-sm"
                              className="text-destructive"
                              aria-label={tList("cancel")}
                              title={tList("cancel")}
                              onClick={() => setToCancel(count)}
                            >
                              <XCircle />
                            </Button>
                          )}
                        </div>
                      </TableCell>
                    </TableRow>
                    {isOpen &&
                      count.lines.map((line) => (
                        <TableRow key={`line-${line.id}`} className="group bg-muted/30">
                          <TableCell />
                          <TableCell colSpan={3}>{line.product_name}</TableCell>
                          <TableCell className="text-right tabular-nums">{line.quantity}</TableCell>
                          <TableCell colSpan={2} className="text-sm text-muted-foreground italic">
                            {line.spoken_text ? `“${line.spoken_text}”` : tList("addedByHand")}
                          </TableCell>
                          <TableCell className="sticky right-0 z-10 bg-background group-hover:bg-muted/50" />
                        </TableRow>
                      ))}
                  </Fragment>
                );
              })}
            </TableBody>
          </Table>
        </div>
      )}

      <AlertDialog open={toCancel !== null} onOpenChange={(open) => !open && setToCancel(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>{tList("cancelTitle")}</AlertDialogTitle>
            <AlertDialogDescription>
              {tList("cancelDescription", { kar: toCancel?.kar_nummer ?? "" })}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>{tList("keep")}</AlertDialogCancel>
            <AlertDialogAction onClick={confirmCancel}>{tList("cancel")}</AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
