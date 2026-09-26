"use client";

// KarTracker's "Plan a kar" screen: pick an active team, then a table (matrix)
// appears with one row per active festival of the season selected in the
// header and a dropdown of the active delivery locations per row. Rows are
// pre-filled with whatever was saved before; Save upserts one record per
// row (season + festival + team) on the backend.

import { useEffect, useRef, useState } from "react";
import { useTranslations } from "next-intl";
import { toast } from "sonner";
import { ApiError, getPlanKar, savePlanKar } from "@/lib/api";
import { useSelectedSeason } from "@/components/shared/season-provider";
import type {
  KarTrackerPlanKarAfleverlocatieOption,
  KarTrackerPlanKarOption,
  KarTrackerPlanKarRow,
} from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";

interface PlanKarProps {
  teams: KarTrackerPlanKarOption[];
  afleverlocaties: KarTrackerPlanKarAfleverlocatieOption[];
}

// A delivery location is shown as its name with its description next to it
// (just the name when it has no description).
function locationLabel(location: KarTrackerPlanKarAfleverlocatieOption): string {
  return location.description ? `${location.name} — ${location.description}` : location.name;
}

// Base UI's Select needs every item to have a non-empty value, so "no
// delivery location chosen" is represented by this sentinel string instead
// of "" — same pattern as the Afleverlocatie screen's NO_KERNLID_VALUE.
const NO_LOCATION_VALUE = "none";

// What was loaded from the backend for one (season, team) combination, plus
// the user's current, possibly unsaved, choice per festival.
interface LoadedPlan {
  key: string;
  rows: KarTrackerPlanKarRow[];
  selections: Record<number, number | null>;
  failed: boolean;
}

export function PlanKar({ teams, afleverlocaties }: PlanKarProps) {
  const t = useTranslations("karTracker.planKar");
  const { selectedSeason } = useSelectedSeason();
  const [teamId, setTeamId] = useState<number | null>(null);
  const [plan, setPlan] = useState<LoadedPlan | null>(null);
  const [isSaving, setIsSaving] = useState(false);

  const seasonId = selectedSeason?.id ?? null;
  // The combination the screen currently wants to show. While `plan.key`
  // differs from it, the matrix for it is still loading.
  const wantedKey = seasonId !== null && teamId !== null ? `${seasonId}:${teamId}` : null;
  const currentWantedKeyRef = useRef(wantedKey);
  useEffect(() => {
    currentWantedKeyRef.current = wantedKey;
  }, [wantedKey]);
  const isLoading = wantedKey !== null && plan?.key !== wantedKey;

  // Load the matrix whenever the team or the header's season changes. The
  // `cancelled` flag drops a response that arrives after the user already
  // switched to something else, so a slow request can't overwrite a newer one.
  useEffect(() => {
    if (seasonId === null || teamId === null) return;
    let cancelled = false;
    const key = `${seasonId}:${teamId}`;

    getPlanKar(seasonId, teamId)
      .then((response) => {
        if (cancelled) return;
        // Pre-fill every row with its saved location (null = none yet).
        const selections: Record<number, number | null> = {};
        for (const row of response.rows) selections[row.festival_id] = row.afleverlocatie_id;
        setPlan({ key, rows: response.rows, selections, failed: false });
      })
      .catch(() => {
        if (cancelled) return;
        setPlan({ key, rows: [], selections: {}, failed: true });
      });

    return () => {
      cancelled = true;
    };
  }, [seasonId, teamId]);

  function updateSelection(festivalId: number, value: string | null) {
    setPlan((current) =>
      current
        ? {
            ...current,
            selections: {
              ...current.selections,
              [festivalId]: value && value !== NO_LOCATION_VALUE ? Number(value) : null,
            },
          }
        : current,
    );
  }

  async function handleSave() {
    if (seasonId === null || teamId === null || plan === null || plan.key !== wantedKey) return;

    setIsSaving(true);
    try {
      // One entry per matrix row; the backend updates existing records and
      // only inserts the ones that don't exist yet.
      const saved = await savePlanKar({
        season_id: seasonId,
        team_id: teamId,
        rows: plan.rows.map((row) => ({
          festival_id: row.festival_id,
          afleverlocatie_id: plan.selections[row.festival_id] ?? null,
        })),
      });
      // Show exactly what the backend stored.
      if (currentWantedKeyRef.current !== wantedKey) return;
      const selections: Record<number, number | null> = {};
      for (const row of saved.rows) selections[row.festival_id] = row.afleverlocatie_id;
      setPlan({ key: plan.key, rows: saved.rows, selections, failed: false });
      toast.success(t("saveSuccess"));
    } catch (error) {
      toast.error(error instanceof ApiError ? error.message : t("saveError"));
    } finally {
      setIsSaving(false);
    }
  }

  const hasMatrix = wantedKey !== null && plan?.key === wantedKey && !plan.failed;

  return (
    <div className="flex flex-col gap-4">
      <div>
        <h1 className="text-2xl font-bold tracking-tight underline">{t("title")}</h1>
        <p className="text-muted-foreground">{t("description")}</p>
      </div>

      {/* The season comes from the header's selector; nothing can be planned without one. */}
      <p className="text-sm">
        <span className="font-medium">{t("activeSeason")}:</span>{" "}
        {selectedSeason ? selectedSeason.name : <span className="text-muted-foreground">{t("noSeason")}</span>}
      </p>

      <div className="flex max-w-sm flex-col gap-2">
        <Label htmlFor="plan-kar-team">{t("teamLabel")}</Label>
        <Select
          value={teamId !== null ? String(teamId) : ""}
          onValueChange={(value) => setTeamId(value ? Number(value) : null)}
        >
          <SelectTrigger id="plan-kar-team">
            <SelectValue>
              {(value: string | null) =>
                value ? teams.find((team) => String(team.id) === value)?.name : t("teamPlaceholder")
              }
            </SelectValue>
          </SelectTrigger>
          <SelectContent>
            {teams.map((team) => (
              <SelectItem key={team.id} value={String(team.id)}>
                {team.name}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        {teams.length === 0 && <p className="text-sm text-muted-foreground">{t("noTeams")}</p>}
      </div>

      {teamId === null && <p className="text-sm text-muted-foreground">{t("selectTeam")}</p>}
      {teamId !== null && seasonId !== null && isLoading && (
        <p className="text-sm text-muted-foreground">{t("loading")}</p>
      )}
      {teamId !== null && seasonId !== null && plan?.key === wantedKey && plan.failed && (
        <p className="text-sm text-destructive">{t("loadError")}</p>
      )}

      {hasMatrix && plan.rows.length === 0 && <p className="text-sm text-muted-foreground">{t("noFestivals")}</p>}

      {hasMatrix && plan.rows.length > 0 && (
        <>
          <div className="rounded-md border [&>div]:max-h-[65vh] [&>div]:overflow-y-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="sticky top-0 z-20 bg-background font-bold underline">
                    {t("columnFestival")}
                  </TableHead>
                  <TableHead className="sticky top-0 z-20 bg-background font-bold underline">
                    {t("columnAfleverlocatie")}
                  </TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {plan.rows.map((row) => {
                  const selected = plan.selections[row.festival_id] ?? null;
                  return (
                    <TableRow key={row.festival_id} className="group">
                      <TableCell className="font-medium">{row.festival_name}</TableCell>
                      <TableCell>
                        <Select
                          value={selected !== null ? String(selected) : NO_LOCATION_VALUE}
                          onValueChange={(value) => updateSelection(row.festival_id, value)}
                        >
                          <SelectTrigger className="w-full max-w-xl" aria-label={t("columnAfleverlocatie")}>
                            <SelectValue>
                              {(value: string | null) => {
                                const location =
                                  value && value !== NO_LOCATION_VALUE
                                    ? afleverlocaties.find((item) => String(item.id) === value)
                                    : undefined;
                                return location ? locationLabel(location) : t("noAfleverlocatie");
                              }}
                            </SelectValue>
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value={NO_LOCATION_VALUE}>{t("noAfleverlocatie")}</SelectItem>
                            {afleverlocaties.map((location) => (
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

          <div>
            <Button onClick={handleSave} disabled={isSaving}>
              {t("save")}
            </Button>
          </div>
        </>
      )}
    </div>
  );
}
