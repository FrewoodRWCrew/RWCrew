"use client";

// The phone's Kar Map: a search box and on/off chips per layer above a map
// that fills the rest of the screen. While typing, a results list covers the
// top of the map; tapping a result flies to its pin. Pins, colours and
// popups come from kar-map-rows.tsx, shared with the desktop Kar Map.

import dynamic from "next/dynamic";
import { useEffect, useMemo, useState } from "react";
import { useTranslations } from "next-intl";
import { karTrackerGroundplanImageUrl } from "@/lib/api";
import type { KarTrackerGroundplan, KarTrackerKarMapResponse } from "@/lib/types";
import { cn } from "@/lib/utils";
import { Input } from "@/components/ui/input";
import type { GroundplanOverlay, KarMapLeafletHandle, KarMapPin } from "@/components/module-2/kar-map-leaflet";
import {
  hasCoordinates,
  LAYER_COLORS,
  textMatches,
  useKarMapRows,
  type LayerKey,
  type MapRow,
} from "@/components/module-2/kar-map-rows";

// Leaflet touches `window` at import time, so the map only runs on the client.
const KarMapLeaflet = dynamic(() => import("@/components/module-2/kar-map-leaflet").then((mod) => mod.KarMapLeaflet), {
  ssr: false,
});

// The map needs a moment after opening before it can fly to a pin.
const FOCUS_DELAY_MS = 300;

interface KarMapPhoneProps {
  data: KarTrackerKarMapResponse;
  groundplans: KarTrackerGroundplan[];
  /** A pin key (e.g. "kar-12") to fly to once the map is open. */
  focusKey?: string;
}

export function KarMapPhone({ data, groundplans, focusKey }: KarMapPhoneProps) {
  const t = useTranslations("karTracker.karMap");
  const tPhone = useTranslations("karTracker.phone.map");
  const [mapHandle, setMapHandle] = useState<KarMapLeafletHandle | null>(null);
  const [search, setSearch] = useState("");

  // Which layers are switched on; every layer starts visible.
  const hasGroundplans = groundplans.length > 0;
  const [visibleLayers, setVisibleLayers] = useState<Record<LayerKey, boolean>>({
    kar: true,
    afleverlocatie: true,
    distributiepunt: true,
  });
  const [showGroundplan, setShowGroundplan] = useState(hasGroundplans);

  const rows = useKarMapRows(data);

  // One Leaflet ImageOverlay per ground plan, placed by its own corners.
  const groundplanOverlays = useMemo<GroundplanOverlay[]>(
    () =>
      groundplans.map((groundplan) => ({
        key: groundplan.id,
        url: karTrackerGroundplanImageUrl(groundplan.id, groundplan.updated_at),
        bounds: [
          [groundplan.sw_latitude, groundplan.sw_longitude],
          [groundplan.ne_latitude, groundplan.ne_longitude],
        ],
      })),
    [groundplans],
  );

  // The pins of the switched-on layers (the search only filters the list).
  const pins = useMemo<KarMapPin[]>(
    () =>
      rows
        .filter((row) => visibleLayers[row.layer] && hasCoordinates(row))
        .map((row) => ({
          key: row.key,
          latitude: row.latitude as number,
          longitude: row.longitude as number,
          color: LAYER_COLORS[row.layer],
          popup: row.popup,
        })),
    [rows, visibleLayers],
  );

  // The search results: rows of switched-on layers matching name or details.
  const matches = useMemo(
    () =>
      search
        ? rows.filter(
            (row) => visibleLayers[row.layer] && (textMatches(row.name, search) || textMatches(row.details, search)),
          )
        : [],
    [rows, visibleLayers, search],
  );

  // Fly to the requested pin once the map is open (from "Toon op kaart").
  useEffect(() => {
    if (!mapHandle || !focusKey) return;
    const timer = window.setTimeout(() => mapHandle.locate(focusKey), FOCUS_DELAY_MS);
    return () => window.clearTimeout(timer);
  }, [mapHandle, focusKey]);

  // Typing narrows the list; exactly one located match flies there straight away.
  function handleSearchChange(value: string) {
    setSearch(value);
    const located = rows.filter(
      (row) =>
        visibleLayers[row.layer] &&
        hasCoordinates(row) &&
        (textMatches(row.name, value) || textMatches(row.details, value)),
    );
    if (value && located.length === 1) mapHandle?.locate(located[0].key);
  }

  // Tapping a result closes the list and flies to its pin.
  function handlePickResult(row: MapRow) {
    setSearch("");
    mapHandle?.locate(row.key);
  }

  function toggleLayer(layer: LayerKey) {
    setVisibleLayers((current) => ({ ...current, [layer]: !current[layer] }));
  }

  const layerChips: { layer: LayerKey; label: string }[] = [
    { layer: "kar", label: t("layerKarren") },
    { layer: "afleverlocatie", label: t("layerAfleverlocaties") },
    { layer: "distributiepunt", label: t("layerDistributiepunten") },
  ];

  return (
    <div className="flex flex-1 flex-col">
      {/* Search and layer switches. */}
      <div className="flex flex-col gap-2 p-3">
        <Input
          value={search}
          onChange={(event) => handleSearchChange(event.target.value)}
          placeholder={t("searchPlaceholder")}
          className="h-11 text-base"
        />
        <div className="flex flex-wrap gap-2">
          {layerChips.map(({ layer, label }) => (
            <LayerChip
              key={layer}
              label={label}
              color={LAYER_COLORS[layer]}
              isOn={visibleLayers[layer]}
              onToggle={() => toggleLayer(layer)}
            />
          ))}
          {hasGroundplans && (
            <LayerChip label={t("layerGroundplan")} isOn={showGroundplan} onToggle={() => setShowGroundplan((on) => !on)} />
          )}
        </div>
      </div>

      {/* The map fills the rest of the screen; search results lie over it. */}
      <div className="relative min-h-[60dvh] flex-1">
        <div className="absolute inset-0">
          <KarMapLeaflet
            pins={pins}
            onReady={setMapHandle}
            showGroundplan={hasGroundplans && showGroundplan}
            groundplanOverlays={groundplanOverlays}
            groundplanOpacity={1}
          />
        </div>
        {search && (
          // z-[1000] keeps the list above Leaflet's own panes and controls.
          <div className="absolute inset-x-0 top-0 z-[1000] max-h-1/2 overflow-y-auto border-b bg-background shadow-md">
            {matches.length === 0 ? (
              <p className="p-3 text-sm text-muted-foreground">{tPhone("noMatches")}</p>
            ) : (
              matches.map((row) => (
                <button
                  key={row.key}
                  type="button"
                  disabled={!hasCoordinates(row)}
                  onClick={() => handlePickResult(row)}
                  className="flex w-full items-center gap-3 border-b px-3 py-2 text-left last:border-b-0 disabled:opacity-60"
                >
                  <span className="size-3 shrink-0 rounded-full" style={{ backgroundColor: LAYER_COLORS[row.layer] }} />
                  <span className="flex min-w-0 flex-col">
                    <span className="font-medium">{row.name}</span>
                    <span className="truncate text-xs text-muted-foreground">
                      {hasCoordinates(row) ? row.details : t("noCoordinates")}
                    </span>
                  </span>
                </button>
              ))
            )}
          </div>
        )}
      </div>
    </div>
  );
}

interface LayerChipProps {
  label: string;
  /** The layer's pin colour, shown as a dot; none for the ground plan. */
  color?: string;
  isOn: boolean;
  onToggle: () => void;
}

/** A round on/off button for one map layer. */
function LayerChip({ label, color, isOn, onToggle }: LayerChipProps) {
  return (
    <button
      type="button"
      onClick={onToggle}
      aria-pressed={isOn}
      className={cn(
        "flex items-center gap-1.5 rounded-full border px-3 py-1.5 text-sm",
        isOn ? "bg-muted font-medium" : "text-muted-foreground opacity-60",
      )}
    >
      {color && <span className="size-2.5 rounded-full" style={{ backgroundColor: color }} />}
      {label}
    </button>
  );
}
