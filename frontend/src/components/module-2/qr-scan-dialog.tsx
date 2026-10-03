"use client";

// A camera dialog that reads one QR code and hands its text back. Used by
// the desktop "Manuele kar beweging" screen to pick a kar by scanning the
// QR code on its karblad. The camera itself lives in qr-scanner.tsx, which
// the phone's full-screen KarScan reuses.

import { useTranslations } from "next-intl";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { QrScanner } from "@/components/module-2/qr-scanner";

interface QrScanDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  /** Called once with the QR code's text; the dialog closes itself right after. */
  onScanned: (text: string) => void;
}

export function QrScanDialog({ open, onOpenChange, onScanned }: QrScanDialogProps) {
  const t = useTranslations("karTracker.actions");

  // Report the scanned text, then close (which also stops the camera).
  function handleScanned(text: string) {
    onScanned(text);
    onOpenChange(false);
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{t("scanTitle")}</DialogTitle>
          <DialogDescription>{t("scanDescription")}</DialogDescription>
        </DialogHeader>
        <QrScanner active={open} onScanned={handleScanned} className="aspect-square w-full rounded-md" />
      </DialogContent>
    </Dialog>
  );
}
