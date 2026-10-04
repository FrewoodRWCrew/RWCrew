"use client";

// Ploeg Wizard step 2: on which afleverlocatie must the goods be delivered,
// per festival chosen in step 1? One dropdown per festival — the same
// festival-row/afleverlocatie-Select layout as KarTracker's "Plan a kar"
// screen (components/module-2/plan-kar.tsx), and saved into that same
// table, so KarTracker sees exactly what the Kernlid chose here. Below the
// table, a map pins the chosen (also not-yet-saved) locations over
// KarTracker's ground plans, like on the "Plan a kar" screen.

import { useEffect, useMemo, useState } from "react";
import { useTranslations } from "next-intl";
import { toast } from "sonner";
import {
  altsienSelectGroundplanImageUrl,
  ApiError,
  listAltsienSelectGroundplans,
  saveAltsienSelectAfleverlocaties,
} from "@/lib/api";
import type { KarTrackerGroundplan } from "@/lib/types";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { formatFestivalPeriod, locationLabel } from "@/components/module-8/wizard/format";
import type { WizardStepProps } from "@/components/module-8/wizard/step-types";
import { AfleverlocatieMap, groupChosenAfleverlocaties } from "@/components/shared/afleverlocatie-map";
import type { GroundplanOverlay } from "@/components/module-2/kar-map-leaflet";

// Base UI's Select needs a real string value for "nothing chosen yet".
const NO_LOCATION_VALUE = "none";

export function AfleverlocatieStep({ state, teamId, seasonId, readOnly, onStateChange, registerSave }: WizardStepProps) {
  const t = useTranslations("altsienSelect.steps.afleverlocaties");
  const festivals = state.festivals.filter((festival) => festival.selected);
  const [draft, setDraft] = useState<Record<number, number | null>>(() =>
    Object.fromEntries(festivals.map((festival) => [festival.festival_id, festival.afleverlocatie_id])),
  );

  // The ground plans for the map, loaded once. If that fails, the map is
  // simply shown without them — the step itself still works.
  const [groundplans, setGroundplans] = useState<KarTrackerGroundplan[]>([]);
  useEffect(() => {
    let cancelled = false;
    listAltsienSelectGroundplans()
      .then((plans) => {
        if (!cancelled) setGroundplans(plans);
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, []);

  // One Leaflet ImageOverlay per ground plan, placed by its own corners.
  const groundplanOverlays = useMemo<GroundplanOverlay[]>(
    () =>
      groundplans.map((groundplan) => ({
        key: groundplan.id,
        url: altsienSelectGroundplanImageUrl(groundplan.id, groundplan.updated_at),
        bounds: [
          [groundplan.sw_latitude, groundplan.sw_longitude],
          [groundplan.ne_latitude, groundplan.ne_longitude],
        ],
      })),
    [groundplans],
  );

  // The distinct locations in the draft, each with its festivals. A location
  // deactivated since isn't among the options, so it's named from the saved
  // choice and listed as "without coordinates".
  const chosenLocations = groupChosenAfleverlocaties(
    festivals.map((festival) => ({
      festivalName: festival.festival_name,
      afleverlocatieId: draft[festival.festival_id] ?? null,
      fallbackName: festival.afleverlocatie_name,
    })),
    (id) => state.afleverlocaties.find((location) => location.id === id),
  );
  // Re-frame the map when the team, season or set of chosen locations changes.
  const mapFitKey = `${seasonId}:${teamId}|${chosenLocations
    .map((location) => location.id)
    .sort((a, b) => a - b)
    .join(",")}`;

  const isDirty = festivals.some((festival) => (draft[festival.festival_id] ?? null) !== festival.afleverlocatie_id);

  // Offer the wizard a saver for the pending choices.
  useEffect(() => {
    registerSave(async () => {
      if (!isDirty) return true;
      try {
        const rows = festivals.map((festival) => ({
          festival_id: festival.festival_id,
          afleverlocatie_id: draft[festival.festival_id] ?? null,
        }));
        onStateChange(await saveAltsienSelectAfleverlocaties(teamId, seasonId, rows));
        toast.success(t("saved"));
        return true;
      } catch (error) {
        toast.error(error instanceof ApiError ? error.message : t("saveFailed"));
        return false;
      }
    });
    return () => registerSave(null);
  });

  if (festivals.length === 0) {
    return <p className="text-sm text-muted-foreground">{t("noFestivals")}</p>;
  }

  return (
    <div className="flex flex-col gap-2">
      <div className="rounded-md border [&>div]:max-h-[65vh] [&>div]:overflow-y-auto">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="sticky top-0 z-20 bg-background font-bold underline">{t("columnFestival")}</TableHead>
              <TableHead className="sticky top-0 z-20 bg-background font-bold underline">{t("columnPeriod")}</TableHead>
              <TableHead className="sticky top-0 z-20 bg-background font-bold underline">
                {t("columnAfleverlocatie")}
              </TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {festivals.map((festival) => {
              const selected = draft[festival.festival_id] ?? null;
              return (
                <TableRow key={festival.festival_id} className="group">
                  <TableCell className="font-medium">{festival.festival_name}</TableCell>
                  <TableCell className="text-muted-foreground tabular-nums">
                    {formatFestivalPeriod(festival.start_date, festival.end_date)}
                  </TableCell>
                  <TableCell>
                    <Select
                      value={selected !== null ? String(selected) : NO_LOCATION_VALUE}
                      disabled={readOnly}
                      onValueChange={(value) =>
                        setDraft((current) => ({
                          ...current,
                          [festival.festival_id]: value && value !== NO_LOCATION_VALUE ? Number(value) : null,
                        }))
                      }
                    >
                      <SelectTrigger className="w-full max-w-xl" aria-label={t("columnAfleverlocatie")}>
                        <SelectValue>
                          {(value: string | null) => {
                            const location =
                              value && value !== NO_LOCATION_VALUE
                                ? state.afleverlocaties.find((item) => String(item.id) === value)
                                : undefined;
                            // A location that was deactivated since is still shown by name.
                            if (!location && value && value !== NO_LOCATION_VALUE && festival.afleverlocatie_name) {
                              return festival.afleverlocatie_name;
                            }
                            return location ? locationLabel(location) : t("noAfleverlocatie");
                          }}
                        </SelectValue>
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value={NO_LOCATION_VALUE}>{t("noAfleverlocatie")}</SelectItem>
                        {state.afleverlocaties.map((location) => (
                          <SelectItem key={location.id} value={String(location.id)}>
                            {locationLabel(location)}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      </div>
      {isDirty && !readOnly && <p className="text-xs text-muted-foreground">{t("unsaved")}</p>}

      <AfleverlocatieMap locations={chosenLocations} groundplanOverlays={groundplanOverlays} fitKey={mapFitKey} />
    </div>
  );
}
