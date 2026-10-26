"use client";

// The red alert next to "Uitgifte & inname" in Atelier's sidebar: how many
// wristband scans are waiting at the counter, so they're noticed on every
// other Atelier screen too. It follows the scanner chosen in this browser on
// the desk screen (the scans that would pop up there); in a browser without a
// desk scanner it counts the waiting scans of every scanner. Polled every few
// seconds, paused while the browser tab is hidden.

import { useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import { listAtelierWaitingScans } from "@/lib/api";
import { useDeskScanner } from "@/components/module-5/desk-scanner";

// How often the count is refreshed, in milliseconds.
const POLL_INTERVAL_MS = 5000;

/** The number of waiting wristband scans (0 while unknown or not allowed). */
function useWaitingScanCount(enabled: boolean): number {
  const scannerId = useDeskScanner();
  // The count with the scanner it belongs to, so a scanner change starts at 0.
  const [result, setResult] = useState<{ scannerId: string | null; count: number } | null>(null);

  useEffect(() => {
    if (!enabled) return;
    let cancelled = false;
    const poll = () => {
      // No need to ask while nobody looks at this tab.
      if (document.visibilityState === "hidden") return;
      listAtelierWaitingScans(scannerId)
        .then((scans) => {
          if (!cancelled) setResult({ scannerId, count: scans.length });
        })
        .catch(() => undefined);
    };
    poll();
    const timer = window.setInterval(poll, POLL_INTERVAL_MS);
    // Refresh straight away when the tab becomes visible again.
    document.addEventListener("visibilitychange", poll);
    return () => {
      cancelled = true;
      window.clearInterval(timer);
      document.removeEventListener("visibilitychange", poll);
    };
  }, [enabled, scannerId]);

  return enabled && result?.scannerId === scannerId ? result.count : 0;
}

interface DeskScanAlertProps {
  /** Whether the user may view the desk (else nothing is asked or shown). */
  enabled: boolean;
}

/** A pulsing red count of waiting wristband scans; nothing when there are none. */
export function DeskScanAlert({ enabled }: DeskScanAlertProps) {
  const t = useTranslations("atelier.desk");
  const count = useWaitingScanCount(enabled);
  if (count === 0) return null;
  return (
    <span
      role="status"
      title={t("scanAlert", { count })}
      aria-label={t("scanAlert", { count })}
      className="relative ml-auto flex h-5 min-w-5 items-center justify-center rounded-full bg-red-600 px-1.5 text-xs font-bold text-white"
    >
      {/* The pulsing ring around the count. */}
      <span className="absolute inset-0 animate-ping rounded-full bg-red-500 opacity-60" />
      <span className="relative">{count}</span>
    </span>
  );
}
