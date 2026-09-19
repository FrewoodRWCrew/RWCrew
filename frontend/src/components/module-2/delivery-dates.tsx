"use client";

// KarTracker's "Delivery Dates" screen: a table with one row per active
// festival of the season selected in the header, each with a delivery date
// and a pick-up date. Rows are pre-filled with whatever was saved before;
// Save upserts one record per festival on the backend (a row with both
// dates cleared removes its record).

import { useEffect, useRef, useState } from "react";
import { useTranslations } from "next-intl";
import { toast } from "sonner";
import { ApiError, getLeverdata, saveLeverdata } from "@/lib/api";
import { useSelectedSeason } from "@/components/shared/season-provider";
import type { KarTrackerLeverdatumRow } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";

// The two dates the user is currently editing for one festival. An empty
// string means "no date" (that is what <input type="date"> reports).
interface DateValues {
  delivery: string;
  pickup: string;
}

// What was loaded from the backend for one season, plus the user's current,
// possibly unsaved, dates per festival.
interface LoadedDates {
  seasonId: number;
  rows: KarTrackerLeverdatumRow[];
  values: Record<number, DateValues>;
  failed: boolean;
}

// Turns the backend's rows into the editable per-festival values.
function toValues(rows: KarTrackerLeverdatumRow[]): Record<number, DateValues> {
  const values: Record<number, DateValues> = {};
  for (const row of rows) {
    values[row.festival_id] = { delivery: row.delivery_date ?? "", pickup: row.pickup_date ?? "" };
  }
  return values;
}

export function DeliveryDates({ canEdit }: { canEdit: boolean }) {
  const t = useTranslations("karTracker.deliveryDates");
  const { selectedSeason } = useSelectedSeason();
  const [loaded, setLoaded] = useState<LoadedDates | null>(null);
  const [isSaving, setIsSaving] = useState(false);

  const seasonId = selectedSeason?.id ?? null;
  const currentSeasonIdRef = useRef(seasonId);
  useEffect(() => {
    currentSeasonIdRef.current = seasonId;
  }, [seasonId]);
  // While the loaded data belongs to a different season than the header's,
  // the table for the current one is still loading.
  const isLoading = seasonId !== null && loaded?.seasonId !== seasonId;
  const hasTable = seasonId !== null && loaded?.seasonId === seasonId && !loaded.failed;

  // Load the table whenever the header's season changes. The `cancelled`
  // flag drops a response that arrives after the user already switched
  // season, so a slow request can't overwrite a newer one.
  useEffect(() => {
    if (seasonId === null) return;
    let cancelled = false;

    getLeverdata(seasonId)
      .then((response) => {
        if (cancelled) return;
        setLoaded({ seasonId, rows: response.rows, values: toValues(response.rows), failed: false });
      })
      .catch(() => {
        if (cancelled) return;
        setLoaded({ seasonId, rows: [], values: {}, failed: true });
      });

    return () => {
      cancelled = true;
    };
  }, [seasonId]);

  function updateDate(festivalId: number, field: keyof DateValues, value: string) {
    setLoaded((current) =>
      current
        ? { ...current, values: { ...current.values, [festivalId]: { ...current.values[festivalId], [field]: value } } }
        : current,
    );
  }

  // A festival's pick-up can't be before its delivery (only checkable when both are filled in).
  function hasDateOrderError(values: DateValues | undefined): boolean {
    return Boolean(values?.delivery && values.pickup && values.pickup < values.delivery);
  }

  const hasAnyOrderError = hasTable && loaded.rows.some((row) => hasDateOrderError(loaded.values[row.festival_id]));

  async function handleSave() {
    if (seasonId === null || loaded === null || loaded.seasonId !== seasonId || hasAnyOrderError) return;

    setIsSaving(true);
    try {
      // One entry per table row; the backend updates existing records,
      // inserts new ones and removes the ones whose dates were both cleared.
      const saved = await saveLeverdata({
        season_id: seasonId,
        rows: loaded.rows.map((row) => ({
          festival_id: row.festival_id,
          delivery_date: loaded.values[row.festival_id]?.delivery || null,
          pickup_date: loaded.values[row.festival_id]?.pickup || null,
        })),
      });
      // Show exactly what the backend stored.
      if (currentSeasonIdRef.current !== seasonId) return;
      setLoaded({ seasonId, rows: saved.rows, values: toValues(saved.rows), failed: false });
      toast.success(t("saveSuccess"));
    } catch (error) {
      toast.error(error instanceof ApiError ? error.message : t("saveError"));
    } finally {
      setIsSaving(false);
    }
  }

  return (
    <div className="flex flex-col gap-4">
      <div>
        <h1 className="text-2xl font-bold tracking-tight underline">{t("title")}</h1>
        <p className="text-muted-foreground">{t("description")}</p>
      </div>

      {/* The season comes from the header's selector; nothing can be entered without one. */}
      <p className="text-sm">
        <span className="font-medium">{t("activeSeason")}:</span>{" "}
        {selectedSeason ? selectedSeason.name : <span className="text-muted-foreground">{t("noSeason")}</span>}
      </p>

      {isLoading && <p className="text-sm text-muted-foreground">{t("loading")}</p>}
      {seasonId !== null && loaded?.seasonId === seasonId && loaded.failed && (
        <p className="text-sm text-destructive">{t("loadError")}</p>
      )}

      {hasTable && loaded.rows.length === 0 && <p className="text-sm text-muted-foreground">{t("noFestivals")}</p>}

      {hasTable && loaded.rows.length > 0 && (
        <>
          <div className="rounded-md border [&>div]:max-h-[65vh] [&>div]:overflow-y-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="sticky top-0 z-20 bg-background font-bold underline">
                    {t("columnFestival")}
                  </TableHead>
                  <TableHead className="sticky top-0 z-20 bg-background font-bold underline">
                    {t("columnDeliveryDate")}
                  </TableHead>
                  <TableHead className="sticky top-0 z-20 bg-background font-bold underline">
                    {t("columnPickupDate")}
                  </TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {loaded.rows.map((row) => {
                  const values = loaded.values[row.festival_id] ?? { delivery: "", pickup: "" };
                  const orderError = hasDateOrderError(values);
                  return (
                    <TableRow key={row.festival_id} className="group">
                      <TableCell className="font-medium">{row.festival_name}</TableCell>
                      <TableCell>
                        <Input
                          type="date"
                          className="w-44"
                          aria-label={t("columnDeliveryDate")}
                          value={values.delivery}
                          disabled={!canEdit}
                          onChange={(event) => updateDate(row.festival_id, "delivery", event.target.value)}
                        />
                      </TableCell>
                      <TableCell>
                        <div className="flex flex-col gap-1">
                          <Input
                            type="date"
                            className="w-44"
                            aria-label={t("columnPickupDate")}
                            aria-invalid={orderError}
                            value={values.pickup}
                            disabled={!canEdit}
                            onChange={(event) => updateDate(row.festival_id, "pickup", event.target.value)}
                          />
                          {orderError && <p className="text-xs text-destructive">{t("dateOrderError")}</p>}
                        </div>
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          </div>

          <div>
            {canEdit && (
              <Button onClick={handleSave} disabled={isSaving || hasAnyOrderError}>
                {t("save")}
              </Button>
            )}
          </div>
        </>
      )}
    </div>
  );
}
