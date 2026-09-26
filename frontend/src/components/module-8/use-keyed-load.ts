"use client";

// Loads data for "whatever the screen currently wants to show", identified
// by a string key (e.g. "season:team"). The same approach as KarTracker's
// plan-kar.tsx: state is only set from the request's own callbacks, a
// response that arrives after the key already changed is dropped (so a slow
// request can't overwrite a newer one), and "loading" simply means the
// loaded key differs from the wanted one.

import { useEffect, useRef, useState } from "react";

interface Loaded<T> {
  key: string;
  data: T | null;
  failed: boolean;
}

export interface KeyedLoad<T> {
  /** The data for the current key, or null while loading/failed/no key. */
  data: T | null;
  isLoading: boolean;
  failed: boolean;
  /** Replace the data for the current key (e.g. with a save's response). */
  setData: (data: T) => void;
  /** Load the current key again. */
  reload: () => void;
}

export function useKeyedLoad<T>(key: string | null, load: () => Promise<T>): KeyedLoad<T> {
  const [loaded, setLoaded] = useState<Loaded<T> | null>(null);
  const [reloadCount, setReloadCount] = useState(0);

  // Always call the latest loader without re-running the effect for a new
  // function identity on every render.
  const loadRef = useRef(load);
  useEffect(() => {
    loadRef.current = load;
  });

  useEffect(() => {
    if (key === null) return;
    let cancelled = false;
    loadRef
      .current()
      .then((data) => {
        if (!cancelled) setLoaded({ key, data, failed: false });
      })
      .catch(() => {
        if (!cancelled) setLoaded({ key, data: null, failed: true });
      });
    return () => {
      cancelled = true;
    };
  }, [key, reloadCount]);

  const isCurrent = key !== null && loaded?.key === key;
  return {
    data: isCurrent ? loaded.data : null,
    isLoading: key !== null && !isCurrent,
    failed: isCurrent && loaded.failed,
    setData: (data: T) => {
      if (key !== null) setLoaded({ key, data, failed: false });
    },
    reload: () => setReloadCount((count) => count + 1),
  };
}
