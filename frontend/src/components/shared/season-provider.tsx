"use client";

// App-wide state for "which season is currently selected" in the header's
// SeasonSelector (see season-selector.tsx). Only ever holds seasons whose
// "periode_open" flag is true, passed down from the server-fetched list in
// the protected layout. The choice is persisted in localStorage so it
// survives page reloads and navigation, and is exposed via useSelectedSeason()
// so other modules can later read it as an automatic filter — that wiring
// itself is future work, this only makes the value available.
//
// This is client-side-only (React context + localStorage): a future module
// that needs to filter using this value on the server would need its own
// mechanism (e.g. a cookie), which isn't set up here.

import { createContext, useContext, useState, useSyncExternalStore } from "react";
import type { Season } from "@/lib/types";

const STORAGE_KEY = "rwcrew.selectedSeasonId";

// Same "only true once mounted in the browser" trick as theme-toggle.tsx's
// useHasMounted(): localStorage is only readable client-side, so the very
// first render (server-rendered, and the first browser render before
// hydration) has to report "nothing selected yet" to avoid a mismatch —
// reading localStorage directly inside a useEffect and calling setState
// from it would work too, but causes an avoidable extra render, so this
// reads it straight from render once mounted instead.
function useHasMounted(): boolean {
  return useSyncExternalStore(
    () => () => {},
    () => true,
    () => false,
  );
}

function readPersistedSeasonId(): number | null {
  const stored = window.localStorage.getItem(STORAGE_KEY);
  return stored ? Number(stored) : null;
}

interface SeasonContextValue {
  seasons: Season[];
  selectedSeasonId: number | null;
  selectedSeason: Season | null;
  setSelectedSeasonId: (seasonId: number | null) => void;
}

const SeasonContext = createContext<SeasonContextValue | null>(null);

interface SeasonProviderProps {
  seasons: Season[];
  children: React.ReactNode;
}

export function SeasonProvider({ seasons, children }: SeasonProviderProps) {
  const hasMounted = useHasMounted();
  // undefined = "no explicit choice made yet this session" — fall back to
  // whatever's persisted in localStorage. Once the visitor picks something
  // (including "none"), that explicit choice takes over instead.
  const [explicitSeasonId, setExplicitSeasonId] = useState<number | null | undefined>(undefined);

  const persistedSeasonId = hasMounted ? readPersistedSeasonId() : null;
  const candidateSeasonId = explicitSeasonId !== undefined ? explicitSeasonId : persistedSeasonId;
  // A persisted/previously-chosen id whose season was since closed or
  // deleted is dropped instead of silently pinning a stale, invalid value.
  const selectedSeasonId =
    candidateSeasonId !== null && seasons.some((season) => season.id === candidateSeasonId) ? candidateSeasonId : null;

  function setSelectedSeasonId(seasonId: number | null) {
    setExplicitSeasonId(seasonId);
    if (seasonId === null) {
      window.localStorage.removeItem(STORAGE_KEY);
    } else {
      window.localStorage.setItem(STORAGE_KEY, String(seasonId));
    }
  }

  const selectedSeason = seasons.find((season) => season.id === selectedSeasonId) ?? null;

  return (
    <SeasonContext.Provider value={{ seasons, selectedSeasonId, selectedSeason, setSelectedSeasonId }}>
      {children}
    </SeasonContext.Provider>
  );
}

export function useSelectedSeason(): SeasonContextValue {
  const context = useContext(SeasonContext);
  if (context === null) {
    throw new Error("useSelectedSeason must be used within a SeasonProvider");
  }
  return context;
}
