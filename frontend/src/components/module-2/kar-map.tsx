"use client";

// KarTracker's "Kar Map" screen: plots Karren, Afleverlocaties and
// Distributiepunten that have coordinates on a Leaflet/OpenStreetMap map,
// with a checkbox per layer to show/hide it, a search box that pans/zooms
// the map to a match, and a resume popup per pin (see module_2/router.py's
// list_kar_map). Rows without coordinates aren't plottable, so they're
// still listed in the side panel below — same sticky-header table pattern
// as Kar Planning (components/module-2/kar-planning.tsx) — instead of
// being hidden outright.

import dynamic from "next/dynamic";
import { useMemo, useState, type ReactNode } from "react";
import { useTranslations } from "next-intl";
import type { KarTrackerGroundplan, KarTrackerKarMapResponse } from "@/lib/types";
import { karTrackerGroundplanImageUrl } from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import type { GroundplanOverlay, KarMapLeafletHandle, KarMapPin } from "@/components/module-2/kar-map-leaflet";

// Leaflet touches `window` at import time, so the actual map component can
// only ever run on the client — loaded with ssr:false to keep it out of
// the server render entirely.
const KarMapLeaflet = dynamic(() => import("@/components/module-2/kar-map-leaflet").then((mod) => mod.KarMapLeaflet), {
  ssr: false,
});

type LayerKey = "kar" | "afleverlocatie" | "distributiepunt";

interface MapRow {
  layer: LayerKey;
  key: string;
  name: string;
  details: string;
  // Labeled content shown in the map pin's popup — kept separate from
  // `details` since each layer shows different fields there than in the
  // side table's terse "Details" column.
  popup: ReactNode;
  latitude: number | null;
  longitude: number | null;
}

// Karren reuse this module's own purple accent; the other two layers get
// their own distinct colors so all three read apart at a glance.
const LAYER_COLORS: Record<LayerKey, string> = {
  kar: "var(--color-purple-600)",
  afleverlocatie: "var(--color-emerald-600)",
  distributiepunt: "var(--color-amber-600)",
};

// Fallback map center when there isn't a single located row to average —
// no organization-wide "home base" coordinate exists elsewhere in the app.
const FALLBACK_CENTER: [number, number] = [50.85, 4.35];

function textMatches(fieldValue: string, filterValue: string): boolean {
  if (!filterValue) return true;
  return fieldValue.toLowerCase().includes(filterValue.toLowerCase());
}

interface KarMapProps {
  initialData: KarTrackerKarMapResponse;
  groundplans: KarTrackerGroundplan[];
}

export function KarMap({ initialData, groundplans }: KarMapProps) {
  const t = useTranslations("karTracker.karMap");
  const [mapHandle, setMapHandle] = useState<KarMapLeafletHandle | null>(null);

  const [showKarren, setShowKarren] = useState(true);
  const [showAfleverlocaties, setShowAfleverlocaties] = useState(true);
  const [showDistributiepunten, setShowDistributiepunten] = useState(true);
  // The ground plans aren't a pin layer (they have no rows/search matches
  // of their own), so they share one plain boolean instead of going through
  // LayerKey/layerVisibility like the three pin layers above — every plan
  // is shown or hidden together.
  const hasGroundplans = groundplans.length > 0;
  const [showGroundplan, setShowGroundplan] = useState(hasGroundplans);
  // How opaque the ground plan overlays are drawn (0 = invisible, 1 = fully
  // solid) — a plain client-side preference, not saved to the backend, so
  // it can be tuned per viewing session without an extra save round-trip.
  const [groundplanOpacity, setGroundplanOpacity] = useState(1);
  const [search, setSearch] = useState("");

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

  const rows = useMemo<MapRow[]>(() => {
    const karRows: MapRow[] = initialData.karren.map((kar) => ({
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
    const afleverlocatieRows: MapRow[] = initialData.afleverlocaties.map((afleverlocatie) => ({
      layer: "afleverlocatie",
      key: `afleverlocatie-${afleverlocatie.id}`,
      name: afleverlocatie.name,
      details: `${afleverlocatie.zone_name} • ${afleverlocatie.distributiepunt_name}`,
      // Afleverlocatie pins show omschrijving / naam / zone as labeled lines.
      popup: (
        <div className="flex flex-col gap-0.5 text-sm">
          <span>
            <span className="font-semibold">{t("popupOmschrijving")}:</span> {afleverlocatie.description ?? t("noDescription")}
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
    const distributiepuntRows: MapRow[] = initialData.distributiepunten.map((distributiepunt) => ({
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
  }, [initialData, t]);

  const layerVisibility: Record<LayerKey, boolean> = {
    kar: showKarren,
    afleverlocatie: showAfleverlocaties,
    distributiepunt: showDistributiepunten,
  };

  const visibleRows = useMemo(
    () =>
      rows.filter(
        (row) => layerVisibility[row.layer] && (textMatches(row.name, search) || textMatches(row.details, search)),
      ),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [rows, showKarren, showAfleverlocaties, showDistributiepunten, search],
  );

  const locatedRows = useMemo(
    () => visibleRows.filter((row) => row.latitude !== null && row.longitude !== null),
    [visibleRows],
  );

  const pins: KarMapPin[] = useMemo(
    () =>
      locatedRows.map((row) => ({
        key: row.key,
        latitude: row.latitude as number,
        longitude: row.longitude as number,
        color: LAYER_COLORS[row.layer],
        popup: row.popup,
      })),
    [locatedRows],
  );

  function handleLocate(row: MapRow) {
    if (row.latitude === null || row.longitude === null) return;
    mapHandle?.locate(row.key);
  }

  // When the search box narrows it down to exactly one located pin,
  // automatically pan/zoom to it rather than requiring an extra click.
  function handleSearchChange(value: string) {
    setSearch(value);
    if (!value) return;
    const matches = rows.filter(
      (row) =>
        layerVisibility[row.layer] &&
        (textMatches(row.name, value) || textMatches(row.details, value)) &&
        row.latitude !== null &&
        row.longitude !== null,
    );
    if (matches.length === 1) {
      mapHandle?.locate(matches[0].key);
    }
  }

  return (
    <div className="flex flex-col gap-4">
      <div>
        <h1 className="text-2xl font-bold tracking-tight underline">{t("title")}</h1>
        <p className="text-muted-foreground">{t("description")}</p>
      </div>

      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex flex-wrap items-center gap-4">
          <div className="flex items-center gap-2">
            <Checkbox id="karmap-layer-karren" checked={showKarren} onCheckedChange={(checked) => setShowKarren(checked === true)} />
            <span className="size-2.5 rounded-full" style={{ backgroundColor: LAYER_COLORS.kar }} />
            <Label htmlFor="karmap-layer-karren">{t("layerKarren")}</Label>
          </div>
          <div className="flex items-center gap-2">
            <Checkbox
              id="karmap-layer-afleverlocaties"
              checked={showAfleverlocaties}
              onCheckedChange={(checked) => setShowAfleverlocaties(checked === true)}
            />
            <span className="size-2.5 rounded-full" style={{ backgroundColor: LAYER_COLORS.afleverlocatie }} />
            <Label htmlFor="karmap-layer-afleverlocaties">{t("layerAfleverlocaties")}</Label>
          </div>
          <div className="flex items-center gap-2">
            <Checkbox
              id="karmap-layer-distributiepunten"
              checked={showDistributiepunten}
              onCheckedChange={(checked) => setShowDistributiepunten(checked === true)}
            />
            <span className="size-2.5 rounded-full" style={{ backgroundColor: LAYER_COLORS.distributiepunt }} />
            <Label htmlFor="karmap-layer-distributiepunten">{t("layerDistributiepunten")}</Label>
          </div>
          <div className="flex items-center gap-2">
            <Checkbox
              id="karmap-layer-groundplan"
              checked={showGroundplan}
              onCheckedChange={(checked) => setShowGroundplan(checked === true)}
              disabled={!hasGroundplans}
            />
            <Label htmlFor="karmap-layer-groundplan">{t("layerGroundplan")}</Label>
          </div>
          {showGroundplan && hasGroundplans && (
            <div className="flex items-center gap-2">
              <Label htmlFor="karmap-groundplan-opacity" className="text-muted-foreground">
                {t("groundplanOpacity")}
              </Label>
              <input
                id="karmap-groundplan-opacity"
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

        <Input
          value={search}
          onChange={(event) => handleSearchChange(event.target.value)}
          placeholder={t("searchPlaceholder")}
          className="sm:max-w-xs"
        />
      </div>

      <div className="h-[65vh] w-full overflow-hidden rounded-md border">
        <KarMapLeaflet
          pins={pins}
          center={FALLBACK_CENTER}
          onReady={setMapHandle}
          showGroundplan={showGroundplan}
          groundplanOverlays={groundplanOverlays}
          groundplanOpacity={groundplanOpacity}
        />
      </div>

      <div className="rounded-md border [&>div]:max-h-[65vh] [&>div]:overflow-y-auto">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="sticky top-0 z-20 bg-background font-bold underline">{t("columnLayer")}</TableHead>
              <TableHead className="sticky top-0 z-20 bg-background font-bold underline">{t("columnName")}</TableHead>
              <TableHead className="sticky top-0 z-20 bg-background font-bold underline">{t("columnDetails")}</TableHead>
              <TableHead className="sticky top-0 z-20 bg-background font-bold underline">{t("columnCoordinates")}</TableHead>
              <TableHead className="sticky top-0 z-20 bg-background font-bold underline">{t("columnLocate")}</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {visibleRows.map((row) => {
              const hasCoordinates = row.latitude !== null && row.longitude !== null;
              return (
                <TableRow key={row.key} className="group">
                  <TableCell>
                    <span className="inline-flex items-center gap-2">
                      <span className="size-2.5 rounded-full" style={{ backgroundColor: LAYER_COLORS[row.layer] }} />
                      {t(row.layer === "kar" ? "layerKarren" : row.layer === "afleverlocatie" ? "layerAfleverlocaties" : "layerDistributiepunten")}
                    </span>
                  </TableCell>
                  <TableCell className="font-medium">{row.name}</TableCell>
                  <TableCell className="text-muted-foreground">{row.details}</TableCell>
                  <TableCell className="text-muted-foreground">
                    {hasCoordinates ? `${row.latitude}, ${row.longitude}` : <Badge variant="outline">{t("noCoordinates")}</Badge>}
                  </TableCell>
                  <TableCell>
                    <Button variant="ghost" size="sm" disabled={!hasCoordinates} onClick={() => handleLocate(row)}>
                      {t("locate")}
                    </Button>
                  </TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}
