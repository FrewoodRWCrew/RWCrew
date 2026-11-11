"use client";

// Remembers the token of an unlocked kar in this browser tab (sessionStorage),
// so reloading the page or coming back from the landing page doesn't ask the
// lock code again. One token per kar number; it ends with the tab or when the
// backend says it expired (2 h, or the lock code changed). Read through
// useSyncExternalStore, so the server render simply sees "no token".
// Storage can be blocked (private mode): every access is wrapped in try/catch
// and the page then just asks the code again.

import { useSyncExternalStore } from "react";

const PREFIX = "rwcrew-kar-inventory:";
const listeners = new Set<() => void>();
// A copy in memory, so the page works even when sessionStorage throws.
const memory = new Map<string, string | null>();

function storageKey(karNumber: string): string {
  return `${PREFIX}${karNumber.trim().toUpperCase()}`;
}

function read(karNumber: string | null): string | null {
  if (!karNumber) return null;
  try {
    return window.sessionStorage.getItem(storageKey(karNumber));
  } catch {
    return null;
  }
}

/** Keep (or with null: forget) the token of a kar, and tell the screens. */
export function storeKarInventoryToken(karNumber: string, token: string | null): void {
  try {
    if (token) window.sessionStorage.setItem(storageKey(karNumber), token);
    else window.sessionStorage.removeItem(storageKey(karNumber));
  } catch {
    // Storage blocked: the token only lives until the next reload.
  }
  memory.set(storageKey(karNumber), token);
  listeners.forEach((listener) => listener());
}

function subscribe(listener: () => void): () => void {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

/** The stored token of this kar (null on the server, without one, or without a kar). */
export function useKarInventoryToken(karNumber: string | null): string | null {
  return useSyncExternalStore(
    subscribe,
    () => {
      if (!karNumber) return null;
      const key = storageKey(karNumber);
      return memory.has(key) ? (memory.get(key) ?? null) : read(karNumber);
    },
    () => null,
  );
}
