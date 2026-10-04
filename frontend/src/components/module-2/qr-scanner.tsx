"use client";

// The live camera view that reads one QR code. Shared by the desktop's
// "Scan QR" dialog (qr-scan-dialog.tsx) and the phone's full-screen KarScan
// (components/phone/module-2/kar-scan.tsx). Works in any modern phone
// browser, also when RWCrew is installed on the home screen, but only over
// HTTPS or on localhost — browsers refuse camera access otherwise.

import { useEffect, useRef, useState } from "react";
import { useTranslations } from "next-intl";
import type { IScannerControls } from "@zxing/browser";
import { cn } from "@/lib/utils";

interface QrScannerProps {
  /** The camera runs only while this is true. Each time it turns true again,
   *  a fresh scan starts (e.g. after an unknown kar number was scanned). */
  active: boolean;
  /** Called once per scan session with the QR code's text; the camera stops
   *  right after, until `active` is switched off and on again. */
  onScanned: (text: string) => void;
  /** Classes for the video itself (its size and shape). */
  className?: string;
}

export function QrScanner({ active, onScanned, className }: QrScannerProps) {
  const t = useTranslations("karTracker.actions");
  // The <video> element, kept in state (via a callback ref) so the camera
  // starts as soon as it has actually been mounted.
  const [video, setVideo] = useState<HTMLVideoElement | null>(null);
  const [cameraError, setCameraError] = useState<string | null>(null);

  // The latest callback, read from inside the camera loop so a re-render of
  // the parent doesn't restart the camera.
  const onScannedRef = useRef(onScanned);
  useEffect(() => {
    onScannedRef.current = onScanned;
  });

  // Start the camera while active, stop it as soon as that ends.
  useEffect(() => {
    if (!active || !video) return;
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
          },
        );
        // Scanning may have been switched off while the camera was starting.
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
      // Forget any camera error, so the next session tries again afresh.
      setCameraError(null);
    };
  }, [active, video, t]);

  return (
    <>
      {cameraError && <p className="text-sm text-destructive">{cameraError}</p>}
      {/* Always mounted (only hidden on an error), so switching back on
          restarts the camera. muted + playsInline are required for iPhones
          to show the live camera inside the page instead of full screen. */}
      <video
        ref={setVideo}
        muted
        playsInline
        className={cn(cameraError ? "hidden" : "bg-black object-cover", className)}
      />
    </>
  );
}
