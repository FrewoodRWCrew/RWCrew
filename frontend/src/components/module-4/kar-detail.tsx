"use client";

// One kar in StockMaster: its contents versus this season's needs (what's
// missing, what's extra), the action buttons in the order of the warehouse
// process (Laden → Vertrekt → Terug → Uitladen → Telling, only those that
// fit the kar's state and the user's rights), the Laadlijst PDF, the
// current trip while the kar is out (with its Vertrekbon) and the kar's
// booking history ("Geschiedenis").

import { useEffect, useState } from "react";
import { FileText } from "lucide-react";
import { useLocale, useTranslations } from "next-intl";
import { toast } from "sonner";
import { Link } from "@/i18n/navigation";
import {
  getStockMasterKar,
  listStockMasterBookings,
  stockMasterBookingPdfUrl,
  stockMasterLoadListPdfUrl,
} from "@/lib/api";
import { formatDateTime } from "@/lib/date-time";
import type { Season, StockMasterAction, StockMasterDocument, StockMasterKarDetail, StockMasterMyPermissions } from "@/lib/types";
import { cn } from "@/lib/utils";
import { buttonVariants } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { KarStatusBadge } from "@/components/module-4/stock-pickers";
import { StockMasterSeasonSelect, useStockMasterSeasonId } from "@/components/module-4/stockmaster-season-select";
import { ACTION_PATHS, STOCKMASTER_BASE, canBook, hasRight } from "@/components/module-4/stockmaster-common";

interface KarDetailProps {
  karId: number;
  seasons: Season[];
  permissions: StockMasterMyPermissions;
}

export function KarDetail({ karId, seasons, permissions }: KarDetailProps) {
  const t = useTranslations("stockMaster");
  const locale = useLocale();
  const seasonId = useStockMasterSeasonId(seasons);
  const [detail, setDetail] = useState<StockMasterKarDetail | null>(null);
  const [history, setHistory] = useState<StockMasterDocument[] | null>(null);
  const canSeeBookings = hasRight(permissions, "bookings", "view");

  useEffect(() => {
    getStockMasterKar(karId, seasonId)
      .then(setDetail)
      .catch(() => toast.error(t("errors.loadFailed")));
  }, [karId, seasonId, t]);

  useEffect(() => {
    if (!canSeeBookings) return;
    listStockMasterBookings({ kar_id: karId, limit: 15 })
      .then((page) => setHistory(page.items))
      .catch(() => setHistory([]));
  }, [karId, canSeeBookings]);

  if (!detail) return <p className="text-sm text-muted-foreground">{t("common.loading")}</p>;

  const { kar } = detail;
  const seasonQuery = seasonId ? `&season=${seasonId}` : "";

  // The actions that fit the kar's state, in process order.
  const actions: StockMasterAction[] = kar.is_out
    ? ["kar_return"]
    : ["kar_load", "kar_dispatch", "kar_unload", "count"];
  const allowedActions = actions.filter((action) =>
    action === "count" ? hasRight(permissions, "count", "view") : canBook(permissions, action),
  );

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <Link href={`${STOCKMASTER_BASE}/kars`} className="text-sm text-muted-foreground underline">
            {t("kars.backToKars")}
          </Link>
          <h1 className="flex items-center gap-3 text-2xl font-bold tracking-tight underline">
            {t("kars.karTitle", { kar: kar.kar_nummer })}
            <KarStatusBadge isOut={kar.is_out} />
          </h1>
          <p className="text-muted-foreground">
            {kar.team_name ?? t("common.noTeam")}
            {kar.kartracker_status ? ` · ${kar.kartracker_status}` : ""}
          </p>
        </div>
        <StockMasterSeasonSelect seasons={seasons} seasonId={seasonId} />
      </div>

      <div className="flex flex-wrap gap-2">
        {allowedActions.map((action) => (
          <Link
            key={action}
            href={`${STOCKMASTER_BASE}${ACTION_PATHS[action]}?kar=${kar.kar_id}${seasonQuery}`}
            className={buttonVariants({ variant: action === allowedActions[0] ? "default" : "outline" })}
          >
            {t(`kars.buttons.${action}`)}
          </Link>
        ))}
        {seasonId !== null && (
          <a
            href={stockMasterLoadListPdfUrl(kar.kar_id, seasonId, locale)}
            target="_blank"
            rel="noreferrer"
            className={buttonVariants({ variant: "outline" })}
          >
            <FileText />
            {t("kars.loadList")}
          </a>
        )}
      </div>

      {kar.is_out && kar.trip && (
        <Card className="border-orange-300 dark:border-orange-500/40">
          <CardHeader>
            <CardTitle>{t("kars.tripTitle")}</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col gap-3 text-sm">
            <p>
              {t("kars.tripInfo", {
                date: formatDateTime(kar.trip.dispatched_at),
                team: kar.trip.team_name ?? t("common.noTeam"),
                festival: kar.trip.festival_name ?? "—",
              })}
            </p>
            <ul className="divide-y">
              {detail.dispatched.map((line) => (
                <li key={line.product_id} className="flex justify-between py-1">
                  <span>{line.name}</span>
                  <span className="font-semibold tabular-nums">{line.quantity}</span>
                </li>
              ))}
            </ul>
            <a
              href={stockMasterBookingPdfUrl(kar.trip.dispatch_document_id, locale)}
              target="_blank"
              rel="noreferrer"
              className={cn(buttonVariants({ variant: "outline", size: "sm" }), "w-fit")}
            >
              <FileText />
              {t("booking.dispatchNote")} {kar.trip.dispatch_doc_number}
            </a>
          </CardContent>
        </Card>
      )}

      {!kar.is_out && (
        <div className="flex flex-col gap-2">
          <h2 className="text-lg font-semibold">
            {t("kars.contentsTitle")}
            {kar.required_total > 0 && (
              <span className="ml-3 text-sm font-normal text-muted-foreground">
                {t("kars.loaded")}: {kar.loaded_toward_required} / {kar.required_total}
              </span>
            )}
          </h2>
          {detail.lines.length === 0 ? (
            <p className="text-sm text-muted-foreground">{t("kars.emptyKar")}</p>
          ) : (
            <div className="rounded-md border [&>div]:max-h-[65vh] [&>div]:overflow-y-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="sticky top-0 z-20 bg-background font-bold underline">{t("common.product")}</TableHead>
                    <TableHead className="sticky top-0 z-20 bg-background font-bold underline">{t("common.bin")}</TableHead>
                    <TableHead className="sticky top-0 z-20 bg-background text-right font-bold underline">{t("kars.needed")}</TableHead>
                    <TableHead className="sticky top-0 z-20 bg-background text-right font-bold underline">{t("kars.inKar")}</TableHead>
                    <TableHead className="sticky top-0 z-20 bg-background text-right font-bold underline">{t("kars.missing")}</TableHead>
                    <TableHead className="sticky top-0 z-20 bg-background text-right font-bold underline">{t("kars.freeAvailable")}</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {detail.lines.map((line) => (
                    <TableRow key={line.product_id}>
                      <TableCell className="font-medium">{line.name}</TableCell>
                      <TableCell className="text-muted-foreground">{line.bin_label ?? t("common.noBin")}</TableCell>
                      <TableCell className="text-right tabular-nums">{line.required || ""}</TableCell>
                      <TableCell className="text-right tabular-nums">{line.in_kar}</TableCell>
                      <TableCell
                        className={cn(
                          "text-right font-semibold tabular-nums",
                          line.missing > 0 && (line.missing > line.free_available ? "text-destructive" : "text-orange-700 dark:text-orange-300"),
                        )}
                      >
                        {line.missing > 0 ? line.missing : line.surplus > 0 ? t("kars.surplus", { count: line.surplus }) : ""}
                      </TableCell>
                      <TableCell className="text-right tabular-nums text-muted-foreground">{line.free_available}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}
        </div>
      )}

      {canSeeBookings && (
        <div className="flex flex-col gap-2">
          <h2 className="text-lg font-semibold">{t("kars.history")}</h2>
          {history === null ? (
            <p className="text-sm text-muted-foreground">{t("common.loading")}</p>
          ) : history.length === 0 ? (
            <p className="text-sm text-muted-foreground">{t("bookings.empty")}</p>
          ) : (
            <ul className="divide-y rounded-md border text-sm">
              {history.map((document) => (
                <li key={document.id} className="flex flex-wrap items-center gap-3 px-3 py-2">
                  <Link href={`${STOCKMASTER_BASE}/bookings/${document.id}`} className="font-medium underline">
                    {document.doc_number}
                  </Link>
                  <span>{t(`docTypes.${document.doc_type}`)}</span>
                  <span className="text-muted-foreground">{formatDateTime(document.created_at)}</span>
                  <span className="text-muted-foreground">{document.created_by_name}</span>
                  <span className="ml-auto tabular-nums">{t("booking.pieces", { count: document.total_quantity })}</span>
                  {document.status === "reversed" && <span className="text-xs text-destructive">{t("bookings.reversed")}</span>}
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}
