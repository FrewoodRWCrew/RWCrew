"use client";

// MasterData's "Festivals per ploeg" screen (nested under "Teams"): per year
// one row per team and one column per festival, with a tick where the team
// works. The same data as step 1 of Altsien Select's Ploeg Wizard
// (MasterData_team_festival, written only by the backend's
// team_festival_service). Changes are a draft until "Opslaan"; unticking a
// cell whose team already has a delivery location there asks first, because
// saving deletes that location. A closed year is read-only. "Kopieer van
// vorig jaar" adds last year's links (matched by festival name) to the draft.

import { useEffect, useMemo, useState, useTransition } from "react";
import { Copy, Save, Undo2 } from "lucide-react";
import { useTranslations } from "next-intl";
import { toast } from "sonner";
import { usePathname, useRouter } from "@/i18n/navigation";
import { ApiError, getTeamFestivalPrevious, saveTeamFestivalGrid } from "@/lib/api";
import type { TeamFestivalChange, TeamFestivalGrid, TeamFestivalOptions, TeamFestivalPrevious } from "@/lib/types";
import { formatDate } from "@/lib/date-time";
import { cn } from "@/lib/utils";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { SearchableSelect } from "@/components/ui/searchable-select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";

interface TeamFestivalGridScreenProps {
  options: TeamFestivalOptions;
  /** The grid of the year the page opened on (null when there are no years). */
  initialGrid: TeamFestivalGrid | null;
}

/** A cell's key in the draft/saved sets: "teamId:festivalId". */
function cellKey(teamId: number, festivalId: number) {
  return `${teamId}:${festivalId}`;
}

/** The saved links of a grid as a set of cell keys. */
function linkSet(pairs: [number, number][]) {
  return new Set(pairs.map(([teamId, festivalId]) => cellKey(teamId, festivalId)));
}

/** "02-07-2026 – 05-07-2026", or one date for a one-day festival. */
function festivalPeriod(startDate: string, endDate: string) {
  return startDate === endDate ? formatDate(startDate) : `${formatDate(startDate)} – ${formatDate(endDate)}`;
}

export function TeamFestivalGridScreen({ options, initialGrid }: TeamFestivalGridScreenProps) {
  const t = useTranslations("masterdata.teamFestivals");
  const router = useRouter();
  const pathname = usePathname();

  const [grid, setGrid] = useState<TeamFestivalGrid | null>(initialGrid);
  // The ticked cells as the user is editing them; equal to the saved links
  // until something is changed.
  const [draft, setDraft] = useState<Set<string>>(() => linkSet(initialGrid?.links ?? []));
  const [teamSearch, setTeamSearch] = useState("");
  const [isSaving, setIsBusy] = useState(false);
  const [isNavigating, startNavigation] = useTransition();
  const isBusy = isSaving || isNavigating;
  // The result of the last "copy from last year", shown above the table.
  const [copyResult, setCopyResult] = useState<{ proposal: TeamFestivalPrevious; added: number } | null>(null);
  // Cells that will lose a delivery location, while the confirmation is open.
  const [pendingRemovals, setPendingRemovals] = useState<{ team: string; festival: string }[] | null>(null);

  const saved = useMemo(() => linkSet(grid?.links ?? []), [grid]);
  const planned = useMemo(() => linkSet(grid?.planned ?? []), [grid]);
  const canChange = grid !== null && grid.editable && grid.can_edit;

  // Every cell whose draft value differs from what is saved.
  const changes: TeamFestivalChange[] = useMemo(() => {
    if (!grid) return [];
    const result: TeamFestivalChange[] = [];
    for (const team of grid.teams) {
      for (const festival of grid.festivals) {
        const key = cellKey(team.id, festival.id);
        if (draft.has(key) !== saved.has(key)) {
          result.push({ team_id: team.id, festival_id: festival.id, selected: draft.has(key) });
        }
      }
    }
    return result;
  }, [grid, draft, saved]);
  const isDirty = changes.length > 0;

  // Warn before leaving the page (reload, close tab) with unsaved changes.
  useEffect(() => {
    if (!isDirty) return;
    function warn(event: BeforeUnloadEvent) {
      event.preventDefault();
    }
    window.addEventListener("beforeunload", warn);
    return () => window.removeEventListener("beforeunload", warn);
  }, [isDirty]);

  // Only the teams matching the search box are shown (and touched by the
  // shift-click shortcuts).
  const visibleTeams = useMemo(() => {
    const query = teamSearch.trim().toLowerCase();
    if (!grid) return [];
    return query ? grid.teams.filter((team) => team.name.toLowerCase().includes(query)) : grid.teams;
  }, [grid, teamSearch]);

  /** Show a backend error, translated when it is one of this screen's codes. */
  function errorMessage(error: unknown, fallback: string) {
    if (error instanceof ApiError && error.message === "season_closed") return t("errors.season_closed");
    return error instanceof ApiError ? error.message : fallback;
  }

  /** Replace the grid (after loading or saving) and reset the draft to it. */
  function showGrid(next: TeamFestivalGrid) {
    setGrid(next);
    setDraft(linkSet(next.links));
    setCopyResult(null);
  }

  function changeSeason(value: string | null) {
    if (!value || Number(value) === grid?.season_id) return;
    if (isDirty && !window.confirm(t("discardConfirm"))) return;
    // The year lives in the address: the page loads that year's grid and
    // remounts this screen with it (so a reload opens the same year).
    startNavigation(() => router.replace(`${pathname}?season=${value}`));
  }

  /** Tick or untick one cell of the draft. A festival that is no longer
   * active can only be unticked (the backend refuses new links to it).
   */
  function setCell(next: Set<string>, teamId: number, festivalId: number, selected: boolean, festivalActive: boolean) {
    const key = cellKey(teamId, festivalId);
    if (selected && !festivalActive && !saved.has(key)) return;
    if (selected) next.add(key);
    else next.delete(key);
  }

  function toggleCell(teamId: number, festivalId: number, selected: boolean, festivalActive: boolean) {
    setDraft((current) => {
      const next = new Set(current);
      setCell(next, teamId, festivalId, selected, festivalActive);
      return next;
    });
  }

  /** Shift-click on a festival: tick every shown team, or untick them all
   * when they are all ticked already.
   */
  function toggleColumn(festivalId: number, festivalActive: boolean) {
    setDraft((current) => {
      const allTicked = visibleTeams.every((team) => current.has(cellKey(team.id, festivalId)));
      const next = new Set(current);
      for (const team of visibleTeams) setCell(next, team.id, festivalId, !allTicked, festivalActive);
      return next;
    });
  }

  /** Shift-click on a team: the same for its whole row. */
  function toggleRow(teamId: number) {
    if (!grid) return;
    setDraft((current) => {
      const allTicked = grid.festivals.every((festival) => current.has(cellKey(teamId, festival.id)));
      const next = new Set(current);
      for (const festival of grid.festivals) setCell(next, teamId, festival.id, !allTicked, festival.active);
      return next;
    });
  }

  async function copyFromPreviousYear() {
    if (!grid) return;
    setIsBusy(true);
    try {
      const proposal = await getTeamFestivalPrevious(grid.season_id);
      // Only adds to the draft: nothing is unticked and nothing is saved yet.
      const newKeys = proposal.links
        .map(([teamId, festivalId]) => cellKey(teamId, festivalId))
        .filter((key) => !draft.has(key));
      setDraft(new Set([...draft, ...newKeys]));
      setCopyResult({ proposal, added: newKeys.length });
    } catch (error) {
      toast.error(errorMessage(error, t("copyFailed")));
    } finally {
      setIsBusy(false);
    }
  }

  /** Save, but first ask when an untick deletes a delivery location. */
  function requestSave() {
    if (!grid) return;
    const removals = changes
      .filter((change) => !change.selected && planned.has(cellKey(change.team_id, change.festival_id)))
      .map((change) => ({
        team: grid.teams.find((team) => team.id === change.team_id)?.name ?? "",
        festival: grid.festivals.find((festival) => festival.id === change.festival_id)?.name ?? "",
      }));
    if (removals.length > 0) setPendingRemovals(removals);
    else void save();
  }

  async function save() {
    if (!grid) return;
    setPendingRemovals(null);
    setIsBusy(true);
    try {
      showGrid(await saveTeamFestivalGrid(grid.season_id, changes));
      toast.success(t("saved"));
    } catch (error) {
      toast.error(errorMessage(error, t("saveFailed")));
    } finally {
      setIsBusy(false);
    }
  }

  // Ticked teams per festival (the draft, so the counts follow the edits).
  function columnCount(festivalId: number) {
    return grid ? grid.teams.filter((team) => draft.has(cellKey(team.id, festivalId))).length : 0;
  }

  function rowCount(teamId: number) {
    return grid ? grid.festivals.filter((festival) => draft.has(cellKey(teamId, festival.id))).length : 0;
  }

  const seasonOptions = options.seasons.map((season) => ({
    value: String(season.id),
    label: season.periode_open ? season.name : t("seasonClosedOption", { name: season.name }),
  }));

  return (
    <div className="flex flex-col gap-4">
      <div>
        <h1 className="text-2xl font-bold tracking-tight underline">{t("title")}</h1>
        <p className="text-sm text-muted-foreground">{t("description")}</p>
      </div>

      {options.seasons.length === 0 || grid === null ? (
        <p className="text-sm text-muted-foreground">{t("noSeasons")}</p>
      ) : (
        <>
          {/* Year + team search + the actions. */}
          <div className="flex flex-wrap items-end gap-3">
            <div className="flex flex-col gap-1">
              <Label htmlFor="team-festival-season">{t("seasonLabel")}</Label>
              <SearchableSelect
                id="team-festival-season"
                value={String(grid.season_id)}
                onValueChange={changeSeason}
                options={seasonOptions}
                disabled={isBusy}
                className="w-48"
              />
            </div>
            <Input
              value={teamSearch}
              onChange={(event) => setTeamSearch(event.target.value)}
              placeholder={t("searchTeam")}
              aria-label={t("searchTeam")}
              className="w-56"
            />
            {canChange && (
              <div className="ml-auto flex flex-wrap items-center gap-2">
                <Button variant="outline" onClick={copyFromPreviousYear} disabled={isBusy || grid.festivals.length === 0}>
                  <Copy className="size-4" />
                  {t("copyPrevious")}
                </Button>
                {isDirty && (
                  <span className="rounded-full bg-orange-500/15 px-2.5 py-1 text-xs font-medium text-orange-700 dark:text-orange-300">
                    {t("changedCount", { count: changes.length })}
                  </span>
                )}
                <Button variant="outline" onClick={() => setDraft(new Set(saved))} disabled={isBusy || !isDirty}>
                  <Undo2 className="size-4" />
                  {t("discard")}
                </Button>
                <Button onClick={requestSave} disabled={isBusy || !isDirty}>
                  <Save className="size-4" />
                  {t("save")}
                </Button>
              </div>
            )}
          </div>

          {/* Why the grid can't be changed, when it can't. */}
          {!grid.editable && <p className="rounded-md border bg-muted/50 px-3 py-2 text-sm">{t("closedNotice")}</p>}
          {grid.editable && !grid.can_edit && (
            <p className="rounded-md border bg-muted/50 px-3 py-2 text-sm">{t("readOnlyNotice")}</p>
          )}

          {/* Summary of the last "copy from last year". */}
          {copyResult && (
            <div className="rounded-md border border-primary/40 bg-primary/5 px-3 py-2 text-sm">
              {copyResult.proposal.previous_season_name === null ? (
                <p>{t("copyNoPrevious")}</p>
              ) : (
                <>
                  <p>
                    {copyResult.added > 0
                      ? t("copyResult", { count: copyResult.added, previous: copyResult.proposal.previous_season_name })
                      : t("copyNothing", { previous: copyResult.proposal.previous_season_name })}{" "}
                    {copyResult.proposal.already_present > 0 &&
                      t("copyAlreadyPresent", { count: copyResult.proposal.already_present })}
                  </p>
                  {copyResult.proposal.unmatched.length > 0 && (
                    <p className="mt-1 text-muted-foreground">
                      {t("copyUnmatched")}{" "}
                      {copyResult.proposal.unmatched
                        .map((item) => t("copyUnmatchedItem", { name: item.festival_name, count: item.team_count }))
                        .join(", ")}
                    </p>
                  )}
                </>
              )}
            </div>
          )}

          {grid.festivals.length === 0 ? (
            <p className="text-sm text-muted-foreground">{t("noFestivals")}</p>
          ) : (
            <>
              {canChange && <p className="text-xs text-muted-foreground">{t("shiftHint")}</p>}
              {/* Capped scroll box: header row and team column stay pinned. */}
              <div className="rounded-md border [&>div]:max-h-[65vh] [&>div]:overflow-y-auto">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead className="sticky top-0 left-0 z-30 min-w-56 bg-background font-bold underline">
                        {t("columnTeam")}
                      </TableHead>
                      {grid.festivals.map((festival) => (
                        <TableHead
                          key={festival.id}
                          className="sticky top-0 z-20 h-auto min-w-36 bg-background py-2 text-center align-bottom"
                        >
                          <button
                            type="button"
                            disabled={!canChange}
                            onClick={(event) => event.shiftKey && toggleColumn(festival.id, festival.active)}
                            className="flex w-full flex-col items-center gap-0.5 disabled:cursor-default"
                          >
                            <span className="font-bold whitespace-normal underline">{festival.name}</span>
                            <span className="text-xs font-normal text-muted-foreground tabular-nums">
                              {festivalPeriod(festival.start_date, festival.end_date)}
                            </span>
                            {!festival.active && (
                              <span className="text-xs font-normal text-orange-700 dark:text-orange-300">
                                {t("inactiveFestival")}
                              </span>
                            )}
                            <span className="text-xs font-normal text-muted-foreground">
                              {t("teamCount", { count: columnCount(festival.id) })}
                            </span>
                          </button>
                        </TableHead>
                      ))}
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {visibleTeams.length === 0 ? (
                      <TableRow>
                        <TableCell colSpan={grid.festivals.length + 1} className="text-center text-muted-foreground">
                          {t("noTeams")}
                        </TableCell>
                      </TableRow>
                    ) : (
                      visibleTeams.map((team) => (
                        <TableRow key={team.id} className="group">
                          <TableCell className="sticky left-0 z-10 bg-background group-hover:bg-muted/50">
                            <button
                              type="button"
                              disabled={!canChange}
                              onClick={(event) => event.shiftKey && toggleRow(team.id)}
                              className="flex flex-col items-start text-left disabled:cursor-default"
                            >
                              <span className="font-medium">
                                {team.name}
                                {!team.active && (
                                  <span className="ml-2 text-xs font-normal text-orange-700 dark:text-orange-300">
                                    {t("inactiveTeam")}
                                  </span>
                                )}
                              </span>
                              <span className="text-xs text-muted-foreground">
                                {t("festivalCount", { count: rowCount(team.id) })}
                              </span>
                            </button>
                          </TableCell>
                          {grid.festivals.map((festival) => {
                            const key = cellKey(team.id, festival.id);
                            const checked = draft.has(key);
                            const changed = checked !== saved.has(key);
                            return (
                              <TableCell
                                key={festival.id}
                                className={cn(
                                  "text-center",
                                  // A changed cell is highlighted until saved.
                                  changed && "bg-orange-500/15 group-hover:bg-orange-500/25",
                                )}
                              >
                                <Checkbox
                                  checked={checked}
                                  disabled={!canChange || (!festival.active && !checked)}
                                  onCheckedChange={(value) =>
                                    toggleCell(team.id, festival.id, value === true, festival.active)
                                  }
                                  aria-label={`${team.name} — ${festival.name}`}
                                />
                              </TableCell>
                            );
                          })}
                        </TableRow>
                      ))
                    )}
                  </TableBody>
                </Table>
              </div>
            </>
          )}
        </>
      )}

      {/* Confirmation when saving deletes delivery locations. */}
      <AlertDialog open={pendingRemovals !== null} onOpenChange={(open) => !open && setPendingRemovals(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>{t("removeConfirmTitle")}</AlertDialogTitle>
            <AlertDialogDescription>{t("removeConfirmDescription")}</AlertDialogDescription>
          </AlertDialogHeader>
          <ul className="max-h-48 list-disc overflow-y-auto pl-5 text-sm">
            {(pendingRemovals ?? []).map((removal) => (
              <li key={`${removal.team}|${removal.festival}`}>
                {removal.team} — {removal.festival}
              </li>
            ))}
          </ul>
          <AlertDialogFooter>
            <AlertDialogCancel>{t("cancel")}</AlertDialogCancel>
            <AlertDialogAction onClick={() => void save()}>{t("removeConfirmAction")}</AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
