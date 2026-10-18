"use client";

// "Plan a kar"'s first screen, the planning overview: every kar of an active
// team, each with how many of its team's festivals already have a delivery
// location this season (progress bar, as on StockMaster's Kar laden), and a
// "Plannen" button that opens the team's festival → afleverlocatie matrix
// (?team=<id>, see plan-kar-screen.tsx). Locations are saved per team, so all
// kars of one team show the same figures. Typing a kar number or team and
// pressing Enter opens it too. Follows the app's list-screen table pattern
// (pinned header and Actions column, capped scroll box).

import { useEffect, useState } from "react";
import { MapPin } from "lucide-react";
import { useTranslations } from "next-intl";
import { toast } from "sonner";
import { useRouter } from "@/i18n/navigation";
import { getPlanKarOverview } from "@/lib/api";
import { useSelectedSeason } from "@/components/shared/season-provider";
import type { KarTrackerPlanKarOverviewRow } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";

/** The page's own route; "?team=<id>" opens one team's matrix (see plan-kar-screen.tsx). */
export const PLAN_KAR_PATH = "/modules/module-2/actions/plan-kar";

// What was loaded for one season (null rows = the request failed).
interface LoadedOverview {
  seasonId: number;
  rows: KarTrackerPlanKarOverviewRow[] | null;
}

export function PlanKarOverview() {
  const t = useTranslations("karTracker.planKar");
  const router = useRouter();
  const { selectedSeason } = useSelectedSeason();
  const seasonId = selectedSeason?.id ?? null;
  const [overview, setOverview] = useState<LoadedOverview | null>(null);
  const [search, setSearch] = useState("");

  // Reload whenever the header's season changes; a late answer for an older
  // season is dropped.
  useEffect(() => {
    if (seasonId === null) return;
    let cancelled = false;
    getPlanKarOverview(seasonId)
      .then((rows) => {
        if (!cancelled) setOverview({ seasonId, rows });
      })
      .catch(() => {
        if (cancelled) return;
        setOverview({ seasonId, rows: null });
        toast.error(t("loadError"));
      });
    return () => {
      cancelled = true;
    };
  }, [seasonId, t]);

  const current = overview !== null && overview.seasonId === seasonId ? overview : null;
  const isLoading = seasonId !== null && current === null;

  // Kars matching the search on kar number or team name.
  const needle = search.trim().toLowerCase();
  const visible = (current?.rows ?? []).filter(
    (row) => !needle || row.kar_nummer.toLowerCase().includes(needle) || row.team_name.toLowerCase().includes(needle),
  );

  /** Open the festival matrix of the kar's team. */
  function openTeam(row: KarTrackerPlanKarOverviewRow) {
    router.push(`${PLAN_KAR_PATH}?team=${row.team_id}`);
  }

  // Enter on an exact kar number (or the only match) opens its team.
  function handleSearchKey(event: React.KeyboardEvent<HTMLInputElement>) {
    if (event.key !== "Enter") return;
    const exact = visible.find((row) => row.kar_nummer.toLowerCase() === needle);
    const target = exact ?? (visible.length === 1 ? visible[0] : null);
    if (target) openTeam(target);
  }

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight underline">{t("title")}</h1>
        <p className="text-muted-foreground">{t("overviewDescription")}</p>
      </div>

      {/* The season comes from the header's selector; nothing can be planned without one. */}
      <p className="text-sm">
        <span className="font-medium">{t("activeSeason")}:</span>{" "}
        {selectedSeason ? selectedSeason.name : <span className="text-muted-foreground">{t("noSeason")}</span>}
      </p>

      <div className="flex w-64 flex-col gap-2">
        <Label htmlFor="plan-kar-search">{t("search")}</Label>
        <Input
          id="plan-kar-search"
          autoFocus
          placeholder={t("searchPlaceholder")}
          value={search}
          onChange={(event) => setSearch(event.target.value)}
          onKeyDown={handleSearchKey}
        />
      </div>

      {isLoading && <p className="text-sm text-muted-foreground">{t("loading")}</p>}
      {current?.rows && visible.length === 0 && <p className="text-sm text-muted-foreground">{t("empty")}</p>}

      {visible.length > 0 && (
        <div className="rounded-md border [&>div]:max-h-[65vh] [&>div]:overflow-y-auto">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="sticky top-0 z-20 bg-background font-bold underline">{t("columnKar")}</TableHead>
                <TableHead className="sticky top-0 z-20 bg-background font-bold underline">
                  {t("columnPlanned")}
                </TableHead>
                <TableHead className="sticky top-0 right-0 z-30 bg-background text-right font-bold underline">
                  {t("columnActions")}
                </TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {visible.map((row) => {
                const hasFestivals = row.festival_count > 0;
                const complete = hasFestivals && row.planned_count >= row.festival_count;
                const percent = hasFestivals ? Math.round((row.planned_count / row.festival_count) * 100) : 0;
                return (
                  <TableRow key={row.kar_id} className="group">
                    <TableCell>
                      <div className="font-medium">{row.kar_nummer}</div>
                      <div className="text-xs text-muted-foreground">{row.team_name}</div>
                    </TableCell>
                    <TableCell>
                      {hasFestivals ? (
                        // Festivals with a delivery location, green once every one has one.
                        <div className="flex flex-col gap-1">
                          <div className="flex min-w-40 max-w-md items-center gap-3">
                            <div
                              className="h-2 flex-1 overflow-hidden rounded-full bg-muted"
                              role="progressbar"
                              aria-valuemin={0}
                              aria-valuemax={row.festival_count}
                              aria-valuenow={row.planned_count}
                            >
                              <div
                                className={complete ? "h-full bg-green-600" : "h-full bg-primary"}
                                style={{ width: `${percent}%` }}
                              />
                            </div>
                            <span className="text-sm text-muted-foreground tabular-nums">
                              {t("festivalsCount", { done: row.planned_count, total: row.festival_count })}
                            </span>
                          </div>
                          {/* The team picked no festivals in Altsien Select yet: every festival counts. */}
                          {row.uses_all_festivals && (
                            <span className="text-xs text-muted-foreground">{t("allFestivalsHint")}</span>
                          )}
                        </div>
                      ) : (
                        <span className="text-sm text-muted-foreground">{t("noFestivals")}</span>
                      )}
                    </TableCell>
                    <TableCell className="sticky right-0 z-10 bg-background group-hover:bg-muted/50">
                      <div className="flex items-center justify-end">
                        <Button size="sm" onClick={() => openTeam(row)}>
                          <MapPin className="size-4" />
                          {t("plan")}
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </div>
      )}
    </div>
  );
}
