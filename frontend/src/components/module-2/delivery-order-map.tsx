"use client";

// The "Kaart" of KarTracker's Leveringsvolgorde screen: the Rock Werchter
// ground plan with every active delivery location as a badge showing its
// number in the tour as it is *now on screen* (unsaved changes included)
// next to the saved one, e.g. "5 (was 3)". Hovering a badge shows the
// location's name. A dashed line follows the tour 1 → n, so an illogical
// order stands out. Reuses the Kar Map's Leaflet component
// (components/module-2/kar-map-leaflet.tsx), like shared/afleverlocatie-map.tsx.

import dynamic from "next/dynamic";
import { useMemo, useState } from "react";
import { useTranslations } from "next-intl";
import type { KarTrackerDeliveryOrderLocation } from "@/lib/types";
import { Checkbox } from "@/components/ui/checkbox";
import { Label } from "@/components/ui/label";
import type { GroundplanOverlay, KarMapPin } from "@/components/module-2/kar-map-leaflet";

// Leaflet touches `window` at import time, so the map only ever runs on the client.
const KarMapLeaflet = dynamic(() => import("@/components/module-2/kar-map-leaflet").then((mod) => mod.KarMapLeaflet), {
  ssr: false,
});

// Badge colours: in the tour unchanged / moved / new, and outside the tour.
const COLOR_UNCHANGED = "#7c3aed";
const COLOR_MOVED = "#d97706";
const COLOR_NEW = "#2563eb";
const COLOR_OUTSIDE = "#6b7280";

interface DeliveryOrderMapProps {
  /** The tour as it is on screen, in order. */
  tour: KarTrackerDeliveryOrderLocation[];
  /** Every active location that is not in the tour. */
  outside: KarTrackerDeliveryOrderLocation[];
  groundplanOverlays: GroundplanOverlay[];
}

/** Whether a location has real coordinates (actual numbers, not just "not null"). */
function isLocated(location: KarTrackerDeliveryOrderLocation): boolean {
  return typeof location.latitude === "number" && typeof location.longitude === "number";
}

export function DeliveryOrderMap({ tour, outside, groundplanOverlays }: DeliveryOrderMapProps) {
  const t = useTranslations("karTracker.deliveryOrder");
  const tMap = useTranslations("afleverlocatieMap");
  const hasGroundplans = groundplanOverlays.length > 0;
  const [showGroundplan, setShowGroundplan] = useState(true);
  const [groundplanOpacity, setGroundplanOpacity] = useState(1);
  const [showRoute, setShowRoute] = useState(true);
  const [showOutside, setShowOutside] = useState(true);

  const pins = useMemo<KarMapPin[]>(() => {
    // Description first, then the name (code) and zone; without a description: name — zone.
    const tooltip = (location: KarTrackerDeliveryOrderLocation) =>
      location.description
        ? `${location.description} — ${location.name} · ${location.zone_name}`
        : `${location.name} — ${location.zone_name}`;

    // The tour: new number, plus the saved one when it is different or missing.
    const tourPins = tour.flatMap((location, index): KarMapPin[] => {
      if (!isLocated(location)) return [];
      const position = index + 1;
      const saved = location.terrein_positie;
      const label =
        saved === null
          ? `${position} (${t("newInTour")})`
          : saved === position
            ? String(position)
            : `${position} (${t("previousPosition", { position: saved })})`;
      const color = saved === null ? COLOR_NEW : saved === position ? COLOR_UNCHANGED : COLOR_MOVED;
      return [
        {
          key: `tour-${location.id}`,
          latitude: location.latitude as number,
          longitude: location.longitude as number,
          color,
          label,
          tooltip: tooltip(location),
          // Tour badges always on top of the grey locations around them.
          zIndexOffset: 1000,
        },
      ];
    });

    // Outside the tour: grey; "was 3" when saving will clear its number.
    const outsidePins = showOutside
      ? outside.filter(isLocated).map(
          (location): KarMapPin => ({
            key: `outside-${location.id}`,
            latitude: location.latitude as number,
            longitude: location.longitude as number,
            color: COLOR_OUTSIDE,
            label:
              location.terrein_positie !== null
                ? t("previousPosition", { position: location.terrein_positie })
                : undefined,
            tooltip: tooltip(location),
          }),
        )
      : [];

    return [...outsidePins, ...tourPins];
  }, [tour, outside, showOutside, t]);

  // The dashed line through the tour, in order (locations without coordinates are skipped).
  const route = useMemo<[number, number][]>(
    () => tour.filter(isLocated).map((location) => [location.latitude as number, location.longitude as number]),
    [tour],
  );

  const unlocated = tour.filter((location) => !isLocated(location));

  return (
    <div className="flex min-h-0 flex-1 flex-col gap-2">
      {/* Layer switches. */}
      <div className="flex flex-wrap items-center gap-4">
        <div className="flex items-center gap-2">
          <Checkbox
            id="delivery-order-map-route"
            checked={showRoute}
            onCheckedChange={(checked) => setShowRoute(checked === true)}
          />
          <Label htmlFor="delivery-order-map-route">{t("showRoute")}</Label>
        </div>
        <div className="flex items-center gap-2">
          <Checkbox
            id="delivery-order-map-outside"
            checked={showOutside}
            onCheckedChange={(checked) => setShowOutside(checked === true)}
          />
          <Label htmlFor="delivery-order-map-outside">{t("showOthers")}</Label>
        </div>
        {hasGroundplans && (
          <div className="flex items-center gap-2">
            <Checkbox
              id="delivery-order-map-groundplan"
              checked={showGroundplan}
              onCheckedChange={(checked) => setShowGroundplan(checked === true)}
            />
            <Label htmlFor="delivery-order-map-groundplan">{tMap("layerGroundplan")}</Label>
          </div>
        )}
        {hasGroundplans && showGroundplan && (
          <div className="flex items-center gap-2">
            <Label htmlFor="delivery-order-map-opacity" className="text-muted-foreground">
              {tMap("groundplanOpacity")}
            </Label>
            <input
              id="delivery-order-map-opacity"
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

      {/* Colour legend of the badges. */}
      <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted-foreground">
        <LegendDot color={COLOR_UNCHANGED} text={t("mapLegendUnchanged")} />
        <LegendDot color={COLOR_MOVED} text={t("mapLegendMoved")} />
        <LegendDot color={COLOR_NEW} text={t("mapLegendNew")} />
        <LegendDot color={COLOR_OUTSIDE} text={t("mapLegendOutside")} />
      </div>

      <div className="min-h-0 flex-1 overflow-hidden rounded-md border">
        <KarMapLeaflet
          pins={pins}
          onReady={() => {}}
          showGroundplan={hasGroundplans && showGroundplan}
          groundplanOverlays={groundplanOverlays}
          groundplanOpacity={groundplanOpacity}
          route={showRoute ? route : undefined}
        />
      </div>

      {unlocated.length > 0 && (
        <p className="text-xs text-muted-foreground">
          {t("noCoordinates", { names: unlocated.map((location) => location.description || location.name).join(", ") })}
        </p>
      )}
    </div>
  );
}

function LegendDot({ color, text }: { color: string; text: string }) {
  return (
    <span className="flex items-center gap-1.5">
      <span className="inline-block size-3 rounded-full border border-white" style={{ background: color }} />
      {text}
    </span>
  );
}
