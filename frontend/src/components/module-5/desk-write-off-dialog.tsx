"use client";

// Openstaand's Afboeken: tick the pieces of one person that will never come
// back. Nothing is ticked at the start, because this takes the pieces out of
// the stock for good. The pieces close, so the person can get that article
// again; the person gets no mail. Needs "create" on atelier.writeoff.

import { useState } from "react";
import { PackageX } from "lucide-react";
import { useTranslations } from "next-intl";
import { toast } from "sonner";
import { writeOffAtelierPersonLines } from "@/lib/api";
import { formatDateNl } from "@/lib/date-time";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { atelierDeskErrorMessage } from "@/components/module-5/desk-common";

/** One open piece of the person. */
export interface WriteOffPiece {
  lineId: number;
  day: string;
  article: string;
  size: string;
}

interface WriteOffDialogProps {
  personId: number;
  personName: string;
  pieces: WriteOffPiece[];
  onClose: () => void;
  onDone: () => void;
}

/** The dialog; the screen mounts it per person, so it always starts empty. */
export function WriteOffDialog({ personId, personName, pieces, onClose, onDone }: WriteOffDialogProps) {
  const t = useTranslations("atelier.open");
  const tDesk = useTranslations("atelier.desk");
  const tStock = useTranslations("atelier.stock");
  const [ticked, setTicked] = useState<number[]>([]);
  const [note, setNote] = useState("");
  const [isBusy, setIsBusy] = useState(false);

  function toggle(lineId: number, isTicked: boolean) {
    setTicked((current) => (isTicked ? [...current, lineId] : current.filter((id) => id !== lineId)));
  }

  async function handleWriteOff() {
    setIsBusy(true);
    try {
      await writeOffAtelierPersonLines(personId, ticked, note.trim() || null);
      toast.success(t("writeOffDone", { name: personName, pieces: ticked.length }));
      onDone();
    } catch (error) {
      toast.error(atelierDeskErrorMessage(tDesk, tStock, error));
    } finally {
      setIsBusy(false);
    }
  }

  return (
    <Dialog open onOpenChange={(open) => !open && onClose()}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{t("writeOffTitle", { name: personName })}</DialogTitle>
          <DialogDescription>{t("writeOffDescription")}</DialogDescription>
        </DialogHeader>
        <div className="flex flex-col gap-2">
          {pieces.map((piece) => (
            <label key={piece.lineId} className="flex items-center gap-3 text-sm">
              <Checkbox
                checked={ticked.includes(piece.lineId)}
                onCheckedChange={(checked) => toggle(piece.lineId, checked === true)}
              />
              {piece.article} · {piece.size} · {formatDateNl(piece.day)}
            </label>
          ))}
        </div>
        <div className="flex flex-col gap-2">
          <Label htmlFor="atelier-write-off-note">{t("writeOffNote")}</Label>
          <Input
            id="atelier-write-off-note"
            autoComplete="off"
            maxLength={400}
            value={note}
            onChange={(event) => setNote(event.target.value)}
          />
        </div>
        <div className="flex justify-end gap-3">
          <Button variant="outline" onClick={onClose}>
            {t("writeOffCancel")}
          </Button>
          <Button variant="destructive" disabled={ticked.length === 0 || isBusy} onClick={() => void handleWriteOff()}>
            <PackageX className="size-4" />
            {t("writeOffConfirm", { pieces: ticked.length })}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
