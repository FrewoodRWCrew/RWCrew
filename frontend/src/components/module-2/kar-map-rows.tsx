"use client";

// The building blocks of the Kar Map, shared by the desktop screen
// (kar-map.tsx) and the phone's map (components/phone/module-2/
// kar-map-phone.tsx), so both show exactly the same pins, colours and
// popups: one MapRow per Kar, Afleverlocatie and Distributiepunt.

import { useMemo, type ReactNode } from "react";
import { useTranslations } from "next-intl";
import type { KarTrackerKarMapResponse } from "@/lib/types";

export type LayerKey = "kar" | "afleverlocatie" | "distributiepunt";

export interface MapRow {
  layer: LayerKey;
  /** Unique per pin, e.g. "kar-12" — also what the map's locate() takes. */
  key: string;
  name: string;
  details: string;
  // Labeled content shown in the map pin's popup — kept separate from
  // `details` since each layer shows different fields there than in the
  // terse one-line summary.
  popup: ReactNode;
  latitude: number | null;
  longitude: number | null;
}

// Karren reuse this module's own purple accent; the other two layers get
// their own distinct colors so all three read apart at a glance.
export const LAYER_COLORS: Record<LayerKey, string> = {
  kar: "var(--color-purple-600)",
  afleverlocatie: "var(--color-emerald-600)",
  distributiepunt: "var(--color-amber-600)",
};

/** Case-insensitive "contains"; an empty filter matches everything. */
export function textMatches(fieldValue: string, filterValue: string): boolean {
  if (!filterValue) return true;
  return fieldValue.toLowerCase().includes(filterValue.toLowerCase());
}

/** Whether a row has coordinates, i.e. can be shown as a pin. */
export function hasCoordinates(row: MapRow): boolean {
  return row.latitude !== null && row.longitude !== null;
}

/** Turns the Kar Map payload into one MapRow per item, all layers together. */
export function useKarMapRows(data: KarTrackerKarMapResponse): MapRow[] {
  const t = useTranslations("karTracker.karMap");

  return useMemo<MapRow[]>(() => {
    const karRows: MapRow[] = data.karren.map((kar) => ({
      layer: "kar",
      key: `kar-${kar.id}`,
      name: kar.kar_nummer,
      details: `${kar.status_name} • ${kar.team_name ?? t("noTeam")}`,
      // Kar pins show kar number / status / ploeg as clearly labeled lines.
      popup: (
        <div className="flex flex-col gap-0.5 text-sm">
          <span>
            <span className="font-semibold">{t("popupKarNummer")}:</span> {kar.kar_nummer}
          </span>
          <span>
            <span className="font-semibold">{t("popupStatus")}:</span> {kar.status_name}
          </span>
          <span>
            <span className="font-semibold">{t("popupPloeg")}:</span> {kar.team_name ?? t("noTeam")}
          </span>
        </div>
      ),
      latitude: kar.latitude,
      longitude: kar.longitude,
    }));
    const afleverlocatieRows: MapRow[] = data.afleverlocaties.map((afleverlocatie) => ({
      layer: "afleverlocatie",
      key: `afleverlocatie-${afleverlocatie.id}`,
      name: afleverlocatie.name,
      details: `${afleverlocatie.zone_name} • ${afleverlocatie.distributiepunt_name}`,
      // Afleverlocatie pins show omschrijving / naam / zone as labeled lines.
      popup: (
        <div className="flex flex-col gap-0.5 text-sm">
          <span>
            <span className="font-semibold">{t("popupOmschrijving")}:</span>{" "}
            {afleverlocatie.description ?? t("noDescription")}
          </span>
          <span>
            <span className="font-semibold">{t("popupNaam")}:</span> {afleverlocatie.name}
          </span>
          <span>
            <span className="font-semibold">{t("popupZone")}:</span> {afleverlocatie.zone_name}
          </span>
        </div>
      ),
      latitude: afleverlocatie.latitude,
      longitude: afleverlocatie.longitude,
    }));
    const distributiepuntRows: MapRow[] = data.distributiepunten.map((distributiepunt) => ({
      layer: "distributiepunt",
      key: `distributiepunt-${distributiepunt.id}`,
      name: distributiepunt.name,
      details: distributiepunt.terrein_positie ?? t("noTerreinPositie"),
      // Distributiepunt pins keep the original generic name + details popup.
      popup: (
        <div className="flex flex-col gap-0.5 text-sm">
          <span className="font-semibold">{distributiepunt.name}</span>
          <span className="text-muted-foreground">{distributiepunt.terrein_positie ?? t("noTerreinPositie")}</span>
        </div>
      ),
      latitude: distributiepunt.latitude,
      longitude: distributiepunt.longitude,
    }));
    return [...karRows, ...afleverlocatieRows, ...distributiepuntRows];
  }, [data, t]);
}
