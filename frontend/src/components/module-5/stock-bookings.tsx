"use client";

// Atelier's "Stock > Boekingen" screen: every stock booking, newest first,
// with a type filter. Each row opens its lines in a dialog, prints its
// booking slip (PDF) and — with "edit" on this screen — can be undone
// ("Ongedaan maken" books the exact opposite; the original stays, marked
// as undone).

import { useState } from "react";
import { Eye, FileText, Undo2 } from "lucide-react";
import { useLocale, useTranslations } from "next-intl";
import { toast } from "sonner";
import {
  atelierStockDocumentPdfUrl,
  getAtelierStockDocument,
  listAtelierStockDocuments,
  reverseAtelierStockDocument,
} from "@/lib/api";
import { formatDateTimeNl } from "@/lib/date-time";
import type { AtelierStockDocument } from "@/lib/types";
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
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Textarea } from "@/components/ui/textarea";
import { ATELIER_STOCK_CHANGED_EVENT, atelierStockErrorMessage } from "@/components/module-5/atelier-stock-common";
import { useKeyedLoad } from "@/components/module-4/use-keyed-load";

const ALL = "all";
const DOC_TYPES = ["receipt", "washed", "write_off", "count", "reversal", "hand_out", "return"] as const;
// The counter desk's bookings can only be undone at the desk (Uitgifte annuleren).
const DESK_TYPES: string[] = ["hand_out", "return"];

interface StockBookingsProps {
  canUndo: boolean;
}

export function StockBookings({ canUndo }: StockBookingsProps) {
  const t = useTranslations("atelier.stock");
  const locale = useLocale();
  const [docType, setDocType] = useState<string>(ALL);
  const documents = useKeyedLoad<AtelierStockDocument[]>(docType, () =>
    listAtelierStockDocuments(docType === ALL ? null : docType),
  );

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight underline">{t("bookings.title")}</h1>
          <p className="text-muted-foreground">{t("bookings.description")}</p>
        </div>
        <div className="flex w-56 flex-col gap-2">
          <Label htmlFor="atelier-bookings-type">{t("bookings.typeFilter")}</Label>
          <Select value={docType} onValueChange={(value) => setDocType(value ?? ALL)}>
            <SelectTrigger id="atelier-bookings-type">
              <SelectValue>{(value: string | null) => (value && value !== ALL ? t(`docTypes.${value}`) : t("bookings.allTypes"))}</SelectValue>
            </SelectTrigger>
            <SelectContent>
              <SelectItem value={ALL}>{t("bookings.allTypes")}</SelectItem>
              {DOC_TYPES.map((type) => (
                <SelectItem key={type} value={type}>
                  {t(`docTypes.${type}`)}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>

      <div className="rounded-md border [&>div]:max-h-[65vh] [&>div]:overflow-y-auto">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="sticky top-0 z-20 bg-background font-bold underline">{t("bookings.number")}</TableHead>
              <TableHead className="sticky top-0 z-20 bg-background font-bold underline">{t("bookings.type")}</TableHead>
              <TableHead className="sticky top-0 z-20 bg-background font-bold underline">{t("bookings.date")}</TableHead>
              <TableHead className="sticky top-0 z-20 bg-background font-bold underline">{t("bookings.by")}</TableHead>
              <TableHead className="sticky top-0 z-20 bg-background text-right font-bold underline">{t("bookings.pieces")}</TableHead>
              <TableHead className="sticky top-0 z-20 bg-background font-bold underline">{t("bookings.info")}</TableHead>
              <TableHead className="sticky top-0 z-20 bg-background font-bold underline">{t("bookings.status")}</TableHead>
              <TableHead className="sticky top-0 right-0 z-30 bg-background text-right font-bold underline">
                {t("columns.actions")}
              </TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {(documents.data ?? []).length === 0 && (
              <TableRow>
                <TableCell colSpan={8} className="text-center text-muted-foreground">
                  {documents.isLoading ? t("loading") : t("bookings.empty")}
                </TableCell>
              </TableRow>
            )}
            {(documents.data ?? []).map((document) => (
              <TableRow key={document.id} className="group">
                <TableCell className="font-mono text-sm">{document.doc_number}</TableCell>
                <TableCell>{t(`docTypes.${document.doc_type}`)}</TableCell>
                <TableCell className="text-sm">{formatDateTimeNl(document.created_at)}</TableCell>
                <TableCell className="text-sm">{document.created_by_name}</TableCell>
                <TableCell className="text-right">{document.total_quantity}</TableCell>
                <TableCell className="max-w-xs text-sm whitespace-normal text-muted-foreground">
                  {[
                    document.reason && t(`reasons.${document.reason}`),
                    document.reference,
                    document.reversal_of_number && t("bookings.undoes", { number: document.reversal_of_number }),
                    document.note,
                  ]
                    .filter(Boolean)
                    .join(" · ")}
                </TableCell>
                <TableCell>
                  {document.status === "reversed" ? (
                    <Badge variant="secondary">{t("bookings.reversed", { number: document.reversed_by_number ?? "" })}</Badge>
                  ) : (
                    t("bookings.posted")
                  )}
                </TableCell>
                <TableCell className="sticky right-0 z-10 bg-background group-hover:bg-muted/50">
                  <div className="flex justify-end gap-1">
                    <DocumentDialog documentId={document.id} docNumber={document.doc_number} />
                    <Button
                      variant="ghost"
                      size="icon"
                      aria-label={t("bookings.pdf")}
                      title={t("bookings.pdf")}
                      onClick={() => window.open(atelierStockDocumentPdfUrl(document.id, locale), "_blank")}
                    >
                      <FileText className="size-4" />
                    </Button>
                    {canUndo &&
                      document.status === "posted" &&
                      document.doc_type !== "reversal" &&
                      !DESK_TYPES.includes(document.doc_type) && (
                      <UndoDialog document={document} onUndone={documents.reload} />
                    )}
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

/** One booking's lines, loaded when the dialog opens. */
function DocumentDialog({ documentId, docNumber }: { documentId: number; docNumber: string }) {
  const t = useTranslations("atelier.stock");
  const tFit = useTranslations("atelier.fits");
  const [isOpen, setIsOpen] = useState(false);
  const detail = useKeyedLoad<AtelierStockDocument>(isOpen ? String(documentId) : null, () =>
    getAtelierStockDocument(documentId),
  );

  const place = (status: string | null) => (status ? t(`statuses.${status}`) : t("outside"));

  return (
    <Dialog open={isOpen} onOpenChange={setIsOpen}>
      <DialogTrigger
        render={
          <Button variant="ghost" size="icon" aria-label={t("bookings.details")} title={t("bookings.details")}>
            <Eye className="size-4" />
          </Button>
        }
      />
      <DialogContent className="sm:max-w-2xl">
        <DialogHeader>
          <DialogTitle>{docNumber}</DialogTitle>
          <DialogDescription>{detail.data ? t(`docTypes.${detail.data.doc_type}`) : t("loading")}</DialogDescription>
        </DialogHeader>
        <div className="rounded-md border [&>div]:max-h-[50vh] [&>div]:overflow-y-auto">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="sticky top-0 z-20 bg-background font-bold underline">{t("columns.article")}</TableHead>
                <TableHead className="sticky top-0 z-20 bg-background font-bold underline">{t("columns.size")}</TableHead>
                <TableHead className="sticky top-0 z-20 bg-background font-bold underline">{t("bookings.from")}</TableHead>
                <TableHead className="sticky top-0 z-20 bg-background font-bold underline">{t("bookings.to")}</TableHead>
                <TableHead className="sticky top-0 z-20 bg-background text-right font-bold underline">{t("bookings.pieces")}</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {(detail.data?.movements ?? []).map((move, index) => (
                <TableRow key={index}>
                  <TableCell>{move.article_name}</TableCell>
                  <TableCell>
                    {move.size_name} · {tFit(move.fit)}
                  </TableCell>
                  <TableCell>{place(move.from_status)}</TableCell>
                  <TableCell>{place(move.to_status)}</TableCell>
                  <TableCell className="text-right">{move.quantity}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      </DialogContent>
    </Dialog>
  );
}

/** "Ongedaan maken" with an optional note, after confirming. */
function UndoDialog({ document, onUndone }: { document: AtelierStockDocument; onUndone: () => void }) {
  const t = useTranslations("atelier.stock");
  const tCommon = useTranslations("common");
  const [isOpen, setIsOpen] = useState(false);
  const [note, setNote] = useState("");
  const [isBusy, setIsBusy] = useState(false);

  async function handleUndo() {
    setIsBusy(true);
    try {
      const reversal = await reverseAtelierStockDocument(document.id, note.trim() || null);
      toast.success(t("bookings.undone", { number: reversal.doc_number }));
      setIsOpen(false);
      setNote("");
      onUndone();
      window.dispatchEvent(new Event(ATELIER_STOCK_CHANGED_EVENT));
    } catch (error) {
      toast.error(atelierStockErrorMessage(t, error));
    } finally {
      setIsBusy(false);
    }
  }

  return (
    <AlertDialog open={isOpen} onOpenChange={setIsOpen}>
      <AlertDialogTrigger
        render={
          <Button variant="ghost" size="icon" aria-label={t("bookings.undo")} title={t("bookings.undo")}>
            <Undo2 className="size-4 text-destructive" />
          </Button>
        }
      />
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>{t("bookings.undoTitle", { number: document.doc_number })}</AlertDialogTitle>
          <AlertDialogDescription>{t("bookings.undoDescription")}</AlertDialogDescription>
        </AlertDialogHeader>
        <Textarea rows={2} placeholder={t("noteLabel")} value={note} onChange={(event) => setNote(event.target.value)} />
        <AlertDialogFooter>
          <AlertDialogCancel>{tCommon("cancel")}</AlertDialogCancel>
          <AlertDialogAction variant="destructive" disabled={isBusy} onClick={handleUndo}>
            {t("bookings.undo")}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}
