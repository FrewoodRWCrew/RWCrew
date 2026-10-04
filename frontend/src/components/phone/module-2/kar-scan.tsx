"use client";

// The KarScan camera: point the phone at the QR code on a kar (it holds just
// the kar number). A known kar opens its movement form; an unknown number
// shows a message and scanning simply continues. There is deliberately no
// typed-number fallback, just like the old phone app.

import { useState } from "react";
import { useTranslations } from "next-intl";
import { toast } from "sonner";
import { useRouter } from "@/i18n/navigation";
import type { KarTrackerKarActionKarOption } from "@/lib/types";
import { QrScanner } from "@/components/module-2/qr-scanner";
import { karTrackerPhoneRoutes } from "@/components/phone/module-2/kartracker-phone-routes";

// How long to wait after an unknown code before scanning again.
const RESCAN_DELAY_MS = 1500;

/** Kar numbers are compared trimmed and ignoring upper/lower case. */
function normalizeKarNummer(value: string): string {
  return value.trim().toLowerCase();
}

export function KarScan({ karren }: { karren: KarTrackerKarActionKarOption[] }) {
  const t = useTranslations("karTracker.phone.scan");
  const router = useRouter();
  // The camera runs while true; it pauses after each scan.
  const [isScanning, setIsScanning] = useState(true);

  function handleScanned(text: string) {
    setIsScanning(false);
    const kar = karren.find((candidate) => normalizeKarNummer(candidate.kar_nummer) === normalizeKarNummer(text));
    if (kar) {
      router.push(karTrackerPhoneRoutes.kar(kar.kar_nummer));
      return;
    }
    // Unknown number: say so, then start a new scan after a short pause (so
    // the same wrong code isn't read again and again straight away).
    toast.error(t("karNotFound", { kar: text.trim() }));
    window.setTimeout(() => setIsScanning(true), RESCAN_DELAY_MS);
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="relative overflow-hidden rounded-xl bg-black">
        <QrScanner active={isScanning} onScanned={handleScanned} className="aspect-[3/4] w-full" />
        {/* The aiming square in the middle of the camera picture. */}
        <div className="pointer-events-none absolute inset-0 flex items-center justify-center">
          <div className="size-56 rounded-2xl border-4 border-primary" />
        </div>
      </div>
      <div className="text-center">
        <p className="font-semibold">{t("title")}</p>
        <p className="text-sm text-muted-foreground">{t("hint")}</p>
      </div>
    </div>
  );
}
