"use client";

// The scanner of this desk, remembered per browser (localStorage) — chosen on
// the "Uitgifte & inname" screen and also read by the sidebar's wristband-scan
// alert. Read through useSyncExternalStore so the server render and the first
// client render agree (no scanner on the server).

import { useSyncExternalStore } from "react";

const SCANNER_STORAGE_KEY = "atelier-desk-scanner";
const SCANNER_CHANGED_EVENT = "atelier-desk-scanner-changed";

function readScanner(): string | null {
  try {
    return window.localStorage.getItem(SCANNER_STORAGE_KEY);
  } catch {
    return null;
  }
}

/** Remember (or forget, with null) this browser's desk scanner. */
export function writeScanner(deviceId: string | null) {
  try {
    if (deviceId) window.localStorage.setItem(SCANNER_STORAGE_KEY, deviceId);
    else window.localStorage.removeItem(SCANNER_STORAGE_KEY);
  } catch {
    // Storage blocked: the choice simply isn't remembered.
  }
  window.dispatchEvent(new Event(SCANNER_CHANGED_EVENT));
}

function subscribeScanner(onChange: () => void) {
  window.addEventListener(SCANNER_CHANGED_EVENT, onChange);
  window.addEventListener("storage", onChange);
  return () => {
    window.removeEventListener(SCANNER_CHANGED_EVENT, onChange);
    window.removeEventListener("storage", onChange);
  };
}

/** This browser's desk scanner (device id), or null when none is chosen. */
export function useDeskScanner(): string | null {
  return useSyncExternalStore(subscribeScanner, readScanner, () => null);
}
