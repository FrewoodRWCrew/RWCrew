"use client";

// A map of the afleverlocaties chosen on a festival/afleverlocatie screen —
// shown below KarTracker's "Plan a kar" matrix and below Altsien Select's
// Ploeg Wizard step 2 (afleverlocaties). One pin per chosen location (with
// the festivals that use it in its popup), drawn over the ground plans
// configured on KarTracker's Grondplan screen. Reuses the Kar Map's Leaflet
// component (components/module-2/kar-map-leaflet.tsx), so pins and overlays
// look exactly the same as there.

import dynamic from "next/dynamic";
import { useMemo, useState } from "react";
import { useTranslations } from "next-intl";
import { Checkbox } from "@/components/ui/checkbox";
import { Label } from "@/components/ui/label";
import type { GroundplanOverlay, KarMapPin } from "@/components/module-2/kar-map-leaflet";

// Leaflet touches `window` at import time, so the map only ever runs on the
// client — same ssr:false loading as the Kar Map screen.
const KarMapLeaflet = dynamic(() => import("@/components/module-2/kar-map-leaflet").then((mod) => mod.KarMapLeaflet), {
  ssr: false,
});

// The Kar Map's afleverlocatie colour, so the pins read the same everywhere.
const AFLEVERLOCATIE_COLOR = "var(--color-emerald-600)";

/** One chosen afleverlocatie plus the festivals it was chosen for. */
export interface ChosenAfleverlocatie {
  id: number;
  name: string;
  description: string | null;
  latitude: number | null;
  longitude: number | null;
  festivals: string[];
}

/** Group festival → location choices into one entry per distinct location.
 * `lookup` resolves a location id to its details; when it can't (e.g. a
 * location that was deactivated since), `fallbackName` names it and it is
 * treated as having no coordinates. */
export function groupChosenAfleverlocaties(
  choices: { festivalName: string; afleverlocatieId: number | null; fallbackName?: string | null }[],
  lookup: (id: number) => Omit<ChosenAfleverlocatie, "festivals"> | undefined,
): ChosenAfleverlocatie[] {
  const byId = new Map<number, ChosenAfleverlocatie>();
  for (const choice of choices) {
    if (choice.afleverlocatieId === null) continue;
    let entry = byId.get(choice.afleverlocatieId);
    if (!entry) {
      const location = lookup(choice.afleverlocatieId);
      entry = location
        ? { ...location, festivals: [] }
        : {
            id: choice.afleverlocatieId,
            name: choice.fallbackName ?? String(choice.afleverlocatieId),
            description: null,
            latitude: null,
            longitude: null,
            festivals: [],
          };
      byId.set(choice.afleverlocatieId, entry);
    }
    entry.festivals.push(choice.festivalName);
  }
  return [...byId.values()];
}

/** Whether a location has real coordinates. Checks for actual numbers (not
 * just "not null"), so a response without the fields at all — e.g. from a
 * backend that wasn't restarted after the fields were added — can never hand
 * Leaflet an undefined position. */
function isLocated(location: ChosenAfleverlocatie): boolean {
  return typeof location.latitude === "number" && typeof location.longitude === "number";
}

interface AfleverlocatieMapProps {
  locations: ChosenAfleverlocatie[];
  groundplanOverlays: GroundplanOverlay[];
  /** Changes whenever the map should re-frame (e.g. another team was picked
   * or a different location was chosen) — see KarMapLeaflet's fitKey. */
  fitKey: string;
}

export function AfleverlocatieMap({ locations, groundplanOverlays, fitKey }: AfleverlocatieMapProps) {
  const t = useTranslations("afleverlocatieMap");
  const hasGroundplans = groundplanOverlays.length > 0;
  const [showGroundplan, setShowGroundplan] = useState(true);
  // Client-side only, like on the Kar Map: not saved anywhere.
  const [groundplanOpacity, setGroundplanOpacity] = useState(1);

  // Only locations with coordinates can be pinned.
  const pins = useMemo<KarMapPin[]>(
    () =>
      locations
        .filter(isLocated)
        .map((location) => ({
          key: `afleverlocatie-${location.id}`,
          latitude: location.latitude as number,
          longitude: location.longitude as number,
          color: AFLEVERLOCATIE_COLOR,
          popup: (
            <div className="flex flex-col gap-0.5 text-sm">
              <span className="font-semibold">{location.name}</span>
              {location.description && <span className="text-muted-foreground">{location.description}</span>}
              <span>
                <span className="font-semibold">{t("popupFestivals")}:</span> {location.festivals.join(", ")}
              </span>
            </div>
          ),
        })),
    [locations, t],
  );

  const unlocated = locations.filter((location) => !isLocated(location));

  return (
    <div className="flex flex-col gap-2">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 className="text-lg font-semibold">{t("title")}</h2>
        {hasGroundplans && (
          <div className="flex flex-wrap items-center gap-4">
            <div className="flex items-center gap-2">
              <Checkbox
                id="afleverlocatie-map-groundplan"
                checked={showGroundplan}
                onCheckedChange={(checked) => setShowGroundplan(checked === true)}
              />
              <Label htmlFor="afleverlocatie-map-groundplan">{t("layerGroundplan")}</Label>
            </div>
            {showGroundplan && (
              <div className="flex items-center gap-2">
                <Label htmlFor="afleverlocatie-map-opacity" className="text-muted-foreground">
                  {t("groundplanOpacity")}
                </Label>
                <input
                  id="afleverlocatie-map-opacity"
                  type="range"
                  min={0}
                  max={1}
                  step={0.05}
                  value={groundplanOpacity}
                  onChange={(event) => setGroundplanOpacity(Number(event.target.value))}
                  className="w-24 accent-primary"
                />
              </div>
            )}
          </div>
        )}
      </div>

      {locations.length === 0 && <p className="text-sm text-muted-foreground">{t("noSelection")}</p>}

      {/* The map stays visible (showing the ground plans) even before anything is chosen. */}
      <div className="h-[45vh] w-full overflow-hidden rounded-md border">
        <KarMapLeaflet
          pins={pins}
          onReady={() => {}}
          showGroundplan={hasGroundplans && showGroundplan}
          groundplanOverlays={groundplanOverlays}
          groundplanOpacity={groundplanOpacity}
          // Only a new team/location pick re-frames — ground plans that load
          // after mount must not pull the map away from its default extent.
          fitKey={fitKey}
        />
      </div>

      {unlocated.length > 0 && (
        <p className="text-xs text-muted-foreground">
          {t("noCoordinates", { names: unlocated.map((location) => location.name).join(", ") })}
        </p>
      )}
    </div>
  );
}
