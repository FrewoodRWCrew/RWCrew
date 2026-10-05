"use client";

// One StockMaster booking: who did what and when (Belgian time), every line
// from → to, links to the booking it undoes / the reversal that undid it,
// the PDF (Boekingsbon, or Vertrekbon for "Kar vertrekt") and "Ongedaan
// maken" — which books the exact opposite as a new booking (nothing is ever
// deleted), with an optional comment.

import { useState } from "react";
import { FileText, Undo2 } from "lucide-react";
import { useLocale, useTranslations } from "next-intl";
import { toast } from "sonner";
import { Link, useRouter } from "@/i18n/navigation";
import { reverseStockMasterBooking, stockMasterBookingPdfUrl } from "@/lib/api";
import { formatDateTime } from "@/lib/date-time";
import type { StockMasterBucket, StockMasterDocument, StockMasterMyPermissions } from "@/lib/types";
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
import { Button, buttonVariants } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Textarea } from "@/components/ui/textarea";
import { STOCKMASTER_BASE, announceStockChanged, hasRight, stockErrorMessage } from "@/components/module-4/stockmaster-common";

interface BookingDetailProps {
  document: StockMasterDocument;
  permissions: StockMasterMyPermissions;
}

export function BookingDetail({ document, permissions }: BookingDetailProps) {
  const t = useTranslations("stockMaster");
  const tDetail = useTranslations("stockMaster.bookingDetail");
  const locale = useLocale();
  const router = useRouter();
  const [comment, setComment] = useState("");
  const [isReversing, setIsReversing] = useState(false);

  const canUndo =
    hasRight(permissions, "bookings", "delete") && document.status === "posted" && document.doc_type !== "reversal";

  function place(bucket: StockMasterBucket, karNummer: string | null) {
    if (bucket === "free") return t("common.freeStock");
    if (bucket === "kar") return `${t("common.kar")} ${karNummer ?? "?"}`;
    return t("common.external");
  }

  async function handleUndo() {
    setIsReversing(true);
    try {
      const reversal = await reverseStockMasterBooking(document.id, comment);
      toast.success(t("booking.undone", { number: document.doc_number }));
      announceStockChanged();
      router.push(`${STOCKMASTER_BASE}/bookings/${reversal.id}`);
    } catch (error) {
      toast.error(stockErrorMessage(t, error));
    } finally {
      setIsReversing(false);
    }
  }

  const facts: [string, React.ReactNode][] = [
    [tDetail("date"), formatDateTime(document.created_at)],
    [tDetail("user"), document.created_by_name],
    [t("common.seasonLabel"), document.season_name],
    [t("common.kar"), document.kar_nummer],
    [tDetail("fromKar"), document.from_kar_nummer],
    [t("common.team"), document.team_name],
    [tDetail("festival"), document.festival_name],
    [tDetail("reference"), document.reference],
    [tDetail("reason"), document.reason_name],
    [tDetail("comment"), document.comment],
    [
      tDetail("undoes"),
      document.reversal_of_id ? (
        <Link href={`${STOCKMASTER_BASE}/bookings/${document.reversal_of_id}`} className="underline">
          {document.reversal_of_number}
        </Link>
      ) : null,
    ],
    [
      tDetail("undoneBy"),
      document.reversed_by_id ? (
        <Link href={`${STOCKMASTER_BASE}/bookings/${document.reversed_by_id}`} className="underline">
          {document.reversed_by_number}
        </Link>
      ) : null,
    ],
  ];

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <Link href={`${STOCKMASTER_BASE}/bookings`} className="text-sm text-muted-foreground underline">
            {tDetail("back")}
          </Link>
          <h1 className="flex items-center gap-3 text-2xl font-bold tracking-tight underline">
            {document.doc_number}
            {document.status === "reversed" && <Badge variant="destructive">{t("bookings.reversed")}</Badge>}
          </h1>
          <p className="text-muted-foreground">{t(`docTypes.${document.doc_type}`)}</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <a
            href={stockMasterBookingPdfUrl(document.id, locale)}
            target="_blank"
            rel="noreferrer"
            className={buttonVariants({ variant: "outline" })}
          >
            <FileText />
            {document.doc_type === "kar_dispatch" ? t("booking.dispatchNote") : t("booking.bookingNote")}
          </a>
          {canUndo && (
            <AlertDialog>
              <AlertDialogTrigger render={<Button variant="destructive" />}>
                <Undo2 />
                {t("booking.undo")}
              </AlertDialogTrigger>
              <AlertDialogContent>
                <AlertDialogHeader>
                  <AlertDialogTitle>{tDetail("undoTitle", { number: document.doc_number })}</AlertDialogTitle>
                  <AlertDialogDescription>{tDetail("undoDescription")}</AlertDialogDescription>
                </AlertDialogHeader>
                <div className="flex flex-col gap-2">
                  <Label htmlFor="undo-comment">{tDetail("undoComment")}</Label>
                  <Textarea id="undo-comment" rows={2} value={comment} onChange={(event) => setComment(event.target.value)} />
                </div>
                <AlertDialogFooter>
                  <AlertDialogCancel>{t("common.cancel")}</AlertDialogCancel>
                  <AlertDialogAction onClick={() => void handleUndo()} disabled={isReversing}>
                    {t("booking.undo")}
                  </AlertDialogAction>
                </AlertDialogFooter>
              </AlertDialogContent>
            </AlertDialog>
          )}
        </div>
      </div>

      <Card>
        <CardContent>
          <dl className="grid grid-cols-1 gap-x-8 gap-y-2 text-sm sm:grid-cols-2">
            {facts
              .filter(([, value]) => value !== null && value !== undefined && value !== "")
              .map(([label, value]) => (
                <div key={label} className="flex gap-3">
                  <dt className="w-32 shrink-0 font-medium text-muted-foreground">{label}</dt>
                  <dd>{value}</dd>
                </div>
              ))}
          </dl>
        </CardContent>
      </Card>

      <div className="rounded-md border [&>div]:max-h-[65vh] [&>div]:overflow-y-auto">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="sticky top-0 z-20 bg-background font-bold underline">{t("common.product")}</TableHead>
              <TableHead className="sticky top-0 z-20 bg-background font-bold underline">{tDetail("from")}</TableHead>
              <TableHead className="sticky top-0 z-20 bg-background font-bold underline">{tDetail("to")}</TableHead>
              <TableHead className="sticky top-0 z-20 bg-background text-right font-bold underline">{t("booking.quantityLabel")}</TableHead>
              <TableHead className="sticky top-0 z-20 bg-background font-bold underline">{tDetail("binThen")}</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {document.lines.map((line, index) => (
              <TableRow key={`${line.product_id}-${index}`}>
                <TableCell className="font-medium">{line.product_name}</TableCell>
                <TableCell>{place(line.from_bucket, line.from_kar_nummer)}</TableCell>
                <TableCell>{place(line.to_bucket, line.to_kar_nummer)}</TableCell>
                <TableCell className="text-right tabular-nums">{line.quantity}</TableCell>
                <TableCell className="text-muted-foreground">{line.bin_snapshot ?? ""}</TableCell>
              </TableRow>
            ))}
            <TableRow className="font-semibold hover:bg-transparent">
              <TableCell colSpan={3}>{tDetail("total")}</TableCell>
              <TableCell className="text-right tabular-nums">{document.total_quantity}</TableCell>
              <TableCell />
            </TableRow>
          </TableBody>
        </Table>
      </div>
    </div>
  );
}
