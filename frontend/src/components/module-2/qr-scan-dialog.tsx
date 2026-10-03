"use client";

// A camera dialog that reads one QR code and hands its text back. Used by
// "Manuele kar beweging" to pick a kar by scanning the QR code on its
// karblad, the same way the old phone app did. Works in any modern phone
// browser (also when RWCrew is installed on the home screen), but only over
// HTTPS or on localhost — browsers refuse camera access otherwise.

import { useEffect, useRef, useState } from "react";
import { useTranslations } from "next-intl";
import type { IScannerControls } from "@zxing/browser";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";

interface QrScanDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  /** Called once with the QR code's text; the dialog closes itself right after. */
  onScanned: (text: string) => void;
}

export function QrScanDialog({ open, onOpenChange, onScanned }: QrScanDialogProps) {
  const t = useTranslations("karTracker.actions");
  // The <video> element, kept in state (via a callback ref) so the camera
  // starts as soon as the dialog has actually mounted it.
  const [video, setVideo] = useState<HTMLVideoElement | null>(null);
  const [cameraError, setCameraError] = useState<string | null>(null);

  // The latest callbacks, read from inside the camera loop so a re-render of
  // the parent doesn't restart the camera.
  const onScannedRef = useRef(onScanned);
  const onOpenChangeRef = useRef(onOpenChange);
  useEffect(() => {
    onScannedRef.current = onScanned;
    onOpenChangeRef.current = onOpenChange;
  });

  // Start the camera while the dialog is open, stop it as soon as it closes.
  useEffect(() => {
    if (!open || !video) return;
    let controls: IScannerControls | null = null;
    let stopped = false;

    async function start(element: HTMLVideoElement) {
      if (!navigator.mediaDevices?.getUserMedia) {
        setCameraError(t("cameraUnsupported"));
        return;
      }
      try {
        // Loaded on demand: the decoder is only needed when someone scans.
        const { BrowserQRCodeReader } = await import("@zxing/browser");
        const reader = new BrowserQRCodeReader();
        // Prefer the back camera; laptops just use the one they have.
        controls = await reader.decodeFromConstraints(
          { video: { facingMode: { ideal: "environment" } } },
          element,
          (result) => {
            if (!result || stopped) return;
            // First hit wins: stop the camera and report the text.
            stopped = true;
            controls?.stop();
            onScannedRef.current(result.getText());
            onOpenChangeRef.current(false);
          },
        );
        // The dialog may have closed while the camera was still starting.
        if (stopped) controls.stop();
      } catch (error) {
        const denied = error instanceof DOMException && error.name === "NotAllowedError";
        setCameraError(denied ? t("cameraDenied") : t("cameraFailed"));
      }
    }

    void start(video);
    return () => {
      stopped = true;
      controls?.stop();
      // Forget any camera error, so the next opening tries again afresh.
      setCameraError(null);
    };
  }, [open, video, t]);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{t("scanTitle")}</DialogTitle>
          <DialogDescription>{t("scanDescription")}</DialogDescription>
        </DialogHeader>
        {cameraError && <p className="text-sm text-destructive">{cameraError}</p>}
        {/* Always mounted (only hidden on an error), so reopening the dialog
            restarts the camera. muted + playsInline are required for iPhones
            to show the live camera inside the page instead of full screen. */}
        <video
          ref={setVideo}
          muted
          playsInline
          className={cameraError ? "hidden" : "aspect-square w-full rounded-md bg-black object-cover"}
        />
      </DialogContent>
    </Dialog>
  );
}
