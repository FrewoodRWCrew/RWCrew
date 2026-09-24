// A small hook for "load something from the server when the screen opens":
// tracks loading / error / data and offers reload() for pull-to-refresh and
// retry buttons. Keeps showing the old data while reloading.

import { useCallback, useEffect, useRef, useState } from "react";

export type AsyncState<T> = {
  data: T | null;
  error: Error | null;
  // true during the very first load (no data yet)
  loading: boolean;
  // true while reloading with data already on screen (pull-to-refresh)
  refreshing: boolean;
  reload: () => Promise<void>;
};

// autoLoad (default true) loads when the screen opens. Screens that reload on
// every focus (e.g. a list that must refresh after editing an item) pass
// { autoLoad: false } and call reload() themselves.
export function useAsync<T>(loader: () => Promise<T>, { autoLoad = true }: { autoLoad?: boolean } = {}): AsyncState<T> {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<Error | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  // Always call the newest loader without re-running the effect on every render.
  const loaderRef = useRef(loader);
  loaderRef.current = loader;

  const reload = useCallback(async () => {
    setRefreshing(true);
    try {
      setData(await loaderRef.current());
      setError(null);
    } catch (caught) {
      setError(caught instanceof Error ? caught : new Error(String(caught)));
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  // Load once when the screen opens.
  useEffect(() => {
    if (autoLoad) void reload();
  }, [reload, autoLoad]);

  return { data, error, loading, refreshing, reload };
}
