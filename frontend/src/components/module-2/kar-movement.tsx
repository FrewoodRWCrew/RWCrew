"use client";

// KarTracker's "Manuele kar beweging" screen: every time a kar is moved, the
// deliverer picks the kar, its new status and the GPS location (the phone's
// own position via "Use my location", or a click on the map), and saves.
// The backend stores the movement in KarTracker_kar_actions with a
// timestamp and the kar's current team, and makes it the kar's latest
// status/location. Below the form, a history table of logged movements.

import dynamic from "next/dynamic";
import { LocateFixed, QrCode, Trash2 } from "lucide-react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useTranslations } from "next-intl";
import { toast } from "sonner";
import { ApiError, createKarAction, deleteKarAction, karTrackerGroundplanImageUrl, listKarActions } from "@/lib/api";
import type {
  KarTrackerGroundplan,
  KarTrackerKarAction,
  KarTrackerKarActionKarOption,
  KarTrackerKarActionLookups,
} from "@/lib/types";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import type { GroundplanOverlay, KarMapLeafletHandle, KarMapPin } from "@/components/module-2/kar-map-leaflet";
import { QrScanDialog } from "@/components/module-2/qr-scan-dialog";

// Leaflet touches `window` at import time, so the map only ever runs on the
// client — same ssr:false loading as the Kar Map screen.
const KarMapLeaflet = dynamic(() => import("@/components/module-2/kar-map-leaflet").then((mod) => mod.KarMapLeaflet), {
  ssr: false,
});

// The key and colour of the single pin marking the chosen location.
const CHOSEN_PIN_KEY = "chosen-location";
const CHOSEN_PIN_COLOR = "var(--color-sky-600)";

// Base UI's Select needs a non-empty value, so "every kar" in the history
// filter is this sentinel instead of "".
const ALL_KARREN_VALUE = "all";

// Formats the backend's UTC timestamp in Belgian local time. A fixed time
// zone (not the runtime's default) keeps server render and browser
// hydration identical.
const DATE_TIME_FORMAT = new Intl.DateTimeFormat("nl-BE", {
  timeZone: "Europe/Brussels",
  year: "numeric",
  month: "2-digit",
  day: "2-digit",
  hour: "2-digit",
  minute: "2-digit",
});

// Coordinates are shown with 6 decimals (about 10 cm), plenty for a kar.
function formatCoordinate(value: number): string {
  return value.toFixed(6);
}

// A kar in the form's dropdown: its number with its team next to it, so the
// deliverer can tell karren apart by team ("B001 — Scouts Wezemaal").
function karOptionLabel(kar: KarTrackerKarActionKarOption, noTeamLabel: string): string {
  return `${kar.kar_nummer} — ${kar.team_name ?? noTeamLabel}`;
}

interface KarMovementProps {
  lookups: KarTrackerKarActionLookups;
  initialActions: KarTrackerKarAction[];
  groundplans: KarTrackerGroundplan[];
  canCreate: boolean;
  canDelete: boolean;
}

export function KarMovement({ lookups, initialActions, groundplans, canCreate, canDelete }: KarMovementProps) {
  const t = useTranslations("karTracker.actions");

  // The kar list is kept in state so a kar's current status can follow
  // what was just logged (it pre-selects the status dropdown).
  const [karren, setKarren] = useState(lookups.karren);
  const [karId, setKarId] = useState<number | null>(null);
  const [statusId, setStatusId] = useState<number | null>(null);
  const [position, setPosition] = useState<{ latitude: number; longitude: number } | null>(null);
  const [isLocating, setIsLocating] = useState(false);
  const [gpsError, setGpsError] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);

  // History table state: the rows shown and the kar filter.
  const [actions, setActions] = useState(initialActions);
  const [filterKarId, setFilterKarId] = useState<number | null>(null);

  // Map layer controls, client-side only like on the Kar Map.
  const hasGroundplans = groundplans.length > 0;
  const [showGroundplan, setShowGroundplan] = useState(true);
  const [groundplanOpacity, setGroundplanOpacity] = useState(1);

  const selectedKar = karren.find((kar) => kar.id === karId) ?? null;

  // Picking a kar pre-selects its current status; the user changes it to
  // the status after the movement.
  function handleKarChange(value: string | null) {
    const kar = karren.find((candidate) => String(candidate.id) === value) ?? null;
    setKarId(kar?.id ?? null);
    setStatusId(kar?.status_id ?? null);
  }

  // The QR code on a karblad holds just the kar number. A scan picks that
  // kar (matched trimmed and ignoring case, like the old phone app) and,
  // when no location was chosen yet, asks for the phone's GPS position.
  const [isScanOpen, setIsScanOpen] = useState(false);
  function handleScanned(text: string) {
    const code = text.trim().toLowerCase();
    const kar = karren.find((candidate) => candidate.kar_nummer.trim().toLowerCase() === code);
    if (!kar) {
      toast.error(t("scanUnknownKar", { code: text.trim() }));
      return;
    }
    handleKarChange(String(kar.id));
    if (position === null) handleUseMyLocation();
  }

  // The map's imperative handle, used to fly to a GPS fix. `flyToken`
  // changes on every GPS fix; the effect below then flies there, after the
  // map has received the new pin.
  const mapHandleRef = useRef<KarMapLeafletHandle | null>(null);
  const [flyToken, setFlyToken] = useState(0);
  useEffect(() => {
    if (flyToken > 0) mapHandleRef.current?.locate(CHOSEN_PIN_KEY);
  }, [flyToken]);
  const handleMapReady = useCallback((handle: KarMapLeafletHandle) => {
    mapHandleRef.current = handle;
  }, []);

  // Ask the browser/phone for its current position. Only works over HTTPS
  // (or on localhost) and once the user allowed location access.
  function handleUseMyLocation() {
    if (!("geolocation" in navigator)) {
      setGpsError(t("gpsUnsupported"));
      return;
    }
    setIsLocating(true);
    setGpsError(null);
    navigator.geolocation.getCurrentPosition(
      (result) => {
        setPosition({ latitude: result.coords.latitude, longitude: result.coords.longitude });
        setIsLocating(false);
        setFlyToken((token) => token + 1);
      },
      (error) => {
        setIsLocating(false);
        setGpsError(error.code === error.PERMISSION_DENIED ? t("gpsDenied") : t("gpsFailed"));
      },
      { enableHighAccuracy: true, timeout: 15000, maximumAge: 0 },
    );
  }

  // A click on the map sets (or moves) the chosen location.
  const handleMapClick = useCallback((latitude: number, longitude: number) => {
    setPosition({ latitude, longitude });
    setGpsError(null);
  }, []);

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

  // The only pin on the map: the chosen location, if any.
  const pins = useMemo<KarMapPin[]>(
    () =>
      position
        ? [
            {
              key: CHOSEN_PIN_KEY,
              latitude: position.latitude,
              longitude: position.longitude,
              color: CHOSEN_PIN_COLOR,
              popup: (
                <span className="text-sm">
                  {formatCoordinate(position.latitude)}, {formatCoordinate(position.longitude)}
                </span>
              ),
            },
          ]
        : [],
    [position],
  );

  // Reload the history whenever the kar filter changes. The `cancelled`
  // flag drops a response that arrives after the filter changed again.
  const isFirstFilterRef = useRef(true);
  useEffect(() => {
    // The initial (unfiltered) list already came from the server.
    if (isFirstFilterRef.current) {
      isFirstFilterRef.current = false;
      return;
    }
    let cancelled = false;
    listKarActions(filterKarId ?? undefined)
      .then((rows) => {
        if (!cancelled) setActions(rows);
      })
      .catch(() => {
        if (!cancelled) toast.error(t("loadError"));
      });
    return () => {
      cancelled = true;
    };
  }, [filterKarId, t]);

  const canSave = karId !== null && statusId !== null && position !== null && !isSaving;

  async function handleSave() {
    if (karId === null || statusId === null || position === null) return;
    setIsSaving(true);
    try {
      const saved = await createKarAction({
        kar_id: karId,
        status_id: statusId,
        latitude: position.latitude,
        longitude: position.longitude,
      });
      toast.success(t("saveSuccess", { kar: saved.kar_nummer }));
      // The kar's current status is now the logged one.
      setKarren((current) =>
        current.map((kar) => (kar.id === saved.kar_id ? { ...kar, status_id: saved.status_id } : kar)),
      );
      // Show the new movement on top, when it matches the current filter.
      if (filterKarId === null || filterKarId === saved.kar_id) {
        setActions((current) => [saved, ...current]);
      }
      // Ready for the next kar.
      setKarId(null);
      setStatusId(null);
      setPosition(null);
    } catch (error) {
      toast.error(error instanceof ApiError ? error.message : t("saveError"));
    } finally {
      setIsSaving(false);
    }
  }

  function handleDeleted(actionId: number) {
    setActions((current) => current.filter((action) => action.id !== actionId));
  }

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight underline">{t("title")}</h1>
        <p className="text-muted-foreground">{t("description")}</p>
      </div>

      {canCreate && (
        <div className="flex flex-col gap-4 rounded-md border p-4">
          <div className="grid gap-4 sm:grid-cols-2">
            {/* The kar that was moved; its team is shown read-only and logged as-is. */}
            <div className="flex flex-col gap-2">
              <Label htmlFor="kar-movement-kar">{t("karLabel")}</Label>
              <div className="flex gap-2">
                <Select value={karId !== null ? String(karId) : ""} onValueChange={handleKarChange}>
                  <SelectTrigger id="kar-movement-kar" className="min-w-0 flex-1">
                    <SelectValue>
                      {(value: string | null) => {
                        const kar = value ? karren.find((candidate) => String(candidate.id) === value) : undefined;
                        return kar ? karOptionLabel(kar, t("noTeam")) : t("karPlaceholder");
                      }}
                    </SelectValue>
                  </SelectTrigger>
                  <SelectContent>
                    {karren.map((kar) => (
                      <SelectItem key={kar.id} value={String(kar.id)}>
                        {karOptionLabel(kar, t("noTeam"))}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                {/* Pick the kar by scanning the QR code on its karblad. */}
                <Button type="button" variant="outline" onClick={() => setIsScanOpen(true)}>
                  <QrCode className="size-4" />
                  {t("scanQr")}
                </Button>
              </div>
              <QrScanDialog open={isScanOpen} onOpenChange={setIsScanOpen} onScanned={handleScanned} />
              {karren.length === 0 && <p className="text-sm text-muted-foreground">{t("noKarren")}</p>}
              {selectedKar && (
                <p className="text-sm">
                  <span className="font-medium">{t("teamLabel")}:</span>{" "}
                  {selectedKar.team_name ?? <span className="text-muted-foreground">{t("noTeam")}</span>}
                </p>
              )}
            </div>

            {/* The kar's status after the movement (from KarStatussen). */}
            <div className="flex flex-col gap-2">
              <Label htmlFor="kar-movement-status">{t("statusLabel")}</Label>
              <Select
                value={statusId !== null ? String(statusId) : ""}
                onValueChange={(value) => setStatusId(value ? Number(value) : null)}
              >
                <SelectTrigger id="kar-movement-status" className="w-full">
                  <SelectValue>
                    {(value: string | null) =>
                      value
                        ? lookups.statuses.find((karStatus) => String(karStatus.id) === value)?.name
                        : t("statusPlaceholder")
                    }
                  </SelectValue>
                </SelectTrigger>
                <SelectContent>
                  {lookups.statuses.map((karStatus) => (
                    <SelectItem key={karStatus.id} value={String(karStatus.id)}>
                      {karStatus.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>

          {/* The GPS location: the device's own position, or a click on the map. */}
          <div className="flex flex-col gap-2">
            <Label>{t("locationLabel")}</Label>
            <div className="flex flex-wrap items-center gap-3">
              <Button type="button" variant="outline" onClick={handleUseMyLocation} disabled={isLocating}>
                <LocateFixed className="size-4" />
                {isLocating ? t("locating") : t("useMyLocation")}
              </Button>
              <span className="text-sm">
                {position ? (
                  `${formatCoordinate(position.latitude)}, ${formatCoordinate(position.longitude)}`
                ) : (
                  <span className="text-muted-foreground">{t("noLocation")}</span>
                )}
              </span>
            </div>
            {gpsError && <p className="text-sm text-destructive">{gpsError}</p>}
            <p className="text-xs text-muted-foreground">{t("mapHint")}</p>
          </div>

          {hasGroundplans && (
            <div className="flex flex-wrap items-center gap-4">
              <div className="flex items-center gap-2">
                <Checkbox
                  id="kar-movement-groundplan"
                  checked={showGroundplan}
                  onCheckedChange={(checked) => setShowGroundplan(checked === true)}
                />
                <Label htmlFor="kar-movement-groundplan">{t("layerGroundplan")}</Label>
              </div>
              {showGroundplan && (
                <div className="flex items-center gap-2">
                  <Label htmlFor="kar-movement-opacity" className="text-muted-foreground">
                    {t("groundplanOpacity")}
                  </Label>
                  <input
                    id="kar-movement-opacity"
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

          <div className="h-[45vh] w-full overflow-hidden rounded-md border">
            <KarMapLeaflet
              pins={pins}
              onReady={handleMapReady}
              showGroundplan={hasGroundplans && showGroundplan}
              groundplanOverlays={groundplanOverlays}
              groundplanOpacity={groundplanOpacity}
              onMapClick={handleMapClick}
            />
          </div>

          <div>
            <Button onClick={handleSave} disabled={!canSave}>
              {t("save")}
            </Button>
          </div>
        </div>
      )}

      {/* History of logged movements, newest first. */}
      <div className="flex flex-col gap-3">
        <div className="flex flex-wrap items-end justify-between gap-3">
          <h2 className="text-lg font-bold underline">{t("historyTitle")}</h2>
          <div className="flex w-full max-w-xs flex-col gap-2">
            <Label htmlFor="kar-movement-filter">{t("filterKarLabel")}</Label>
            <Select
              value={filterKarId !== null ? String(filterKarId) : ALL_KARREN_VALUE}
              onValueChange={(value) =>
                setFilterKarId(value && value !== ALL_KARREN_VALUE ? Number(value) : null)
              }
            >
              <SelectTrigger id="kar-movement-filter" className="w-full">
                <SelectValue>
                  {(value: string | null) =>
                    value && value !== ALL_KARREN_VALUE
                      ? karren.find((kar) => String(kar.id) === value)?.kar_nummer
                      : t("filterAllKarren")
                  }
                </SelectValue>
              </SelectTrigger>
              <SelectContent>
                <SelectItem value={ALL_KARREN_VALUE}>{t("filterAllKarren")}</SelectItem>
                {karren.map((kar) => (
                  <SelectItem key={kar.id} value={String(kar.id)}>
                    {kar.kar_nummer}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>

        {actions.length === 0 ? (
          <p className="text-sm text-muted-foreground">{t("noHistory")}</p>
        ) : (
          <div className="rounded-md border [&>div]:max-h-[65vh] [&>div]:overflow-y-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="sticky top-0 z-20 bg-background font-bold underline">
                    {t("columnRecordedAt")}
                  </TableHead>
                  <TableHead className="sticky top-0 z-20 bg-background font-bold underline">
                    {t("columnKar")}
                  </TableHead>
                  <TableHead className="sticky top-0 z-20 bg-background font-bold underline">
                    {t("columnStatus")}
                  </TableHead>
                  <TableHead className="sticky top-0 z-20 bg-background font-bold underline">
                    {t("columnTeam")}
                  </TableHead>
                  <TableHead className="sticky top-0 z-20 bg-background font-bold underline">
                    {t("columnLatitude")}
                  </TableHead>
                  <TableHead className="sticky top-0 z-20 bg-background font-bold underline">
                    {t("columnLongitude")}
                  </TableHead>
                  <TableHead className="sticky top-0 z-20 bg-background font-bold underline">
                    {t("columnUser")}
                  </TableHead>
                  {canDelete && (
                    <TableHead className="sticky top-0 right-0 z-30 bg-background text-right font-bold underline">
                      {t("columnActions")}
                    </TableHead>
                  )}
                </TableRow>
              </TableHeader>
              <TableBody>
                {actions.map((action) => (
                  <TableRow key={action.id} className="group">
                    <TableCell className="whitespace-nowrap">
                      {DATE_TIME_FORMAT.format(new Date(action.recorded_at))}
                    </TableCell>
                    <TableCell className="font-medium">{action.kar_nummer}</TableCell>
                    <TableCell>{action.status_name}</TableCell>
                    <TableCell>{action.team_name ?? ""}</TableCell>
                    <TableCell className="tabular-nums">{formatCoordinate(action.latitude)}</TableCell>
                    <TableCell className="tabular-nums">{formatCoordinate(action.longitude)}</TableCell>
                    <TableCell className="text-muted-foreground">{action.user_name ?? ""}</TableCell>
                    {canDelete && (
                      <TableCell className="sticky right-0 z-10 bg-background text-right group-hover:bg-muted/50">
                        <DeleteKarActionButton action={action} onDeleted={handleDeleted} />
                      </TableCell>
                    )}
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        )}
      </div>
    </div>
  );
}

interface DeleteKarActionButtonProps {
  action: KarTrackerKarAction;
  onDeleted: (actionId: number) => void;
}

/** The trash button + confirmation dialog for one logged movement. */
function DeleteKarActionButton({ action, onDeleted }: DeleteKarActionButtonProps) {
  const t = useTranslations("karTracker.actions");
  const tCommon = useTranslations("common");
  const [isOpen, setIsOpen] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);

  async function handleConfirmDelete() {
    setIsDeleting(true);
    try {
      await deleteKarAction(action.id);
      toast.success(t("deleted"));
      onDeleted(action.id);
      setIsOpen(false);
    } catch (error) {
      toast.error(error instanceof ApiError ? error.message : t("deleteFailed"));
    } finally {
      setIsDeleting(false);
    }
  }

  return (
    <AlertDialog open={isOpen} onOpenChange={setIsOpen}>
      <AlertDialogTrigger
        render={
          <Button variant="ghost" size="icon" aria-label={t("delete")} title={t("delete")}>
            <Trash2 className="size-4 text-destructive" />
          </Button>
        }
      />
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>{t("deleteConfirmTitle")}</AlertDialogTitle>
          <AlertDialogDescription>
            {t("deleteConfirmDescription", {
              kar: action.kar_nummer,
              time: DATE_TIME_FORMAT.format(new Date(action.recorded_at)),
            })}
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel>{tCommon("cancel")}</AlertDialogCancel>
          <AlertDialogAction variant="destructive" disabled={isDeleting} onClick={handleConfirmDelete}>
            {t("delete")}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}
