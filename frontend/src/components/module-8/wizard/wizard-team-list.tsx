"use client";

// The Ploeg Wizard's entry screen: the teams this user may fill in (their
// own teams as Altsien Kernlid, or every team for the organisation), each
// with a progress bar over the wizard's steps, a count of still-open
// special requests, and buttons to start/continue its wizard or open its
// Ploegfiche. Follows the app's list-screen table pattern (pinned header
// and Actions column, capped scroll box).

import { FileText, Play } from "lucide-react";
import { useTranslations } from "next-intl";
import { Link } from "@/i18n/navigation";
import { listAltsienSelectTeams } from "@/lib/api";
import type { AltsienSelectStep, AltsienSelectTeamSummary, Season } from "@/lib/types";
import { buttonVariants } from "@/components/ui/button";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { AltsienSeasonSelect, useAltsienSeasonId } from "@/components/module-8/altsien-season-select";
import { useKeyedLoad } from "@/components/module-8/use-keyed-load";

interface WizardTeamListProps {
  seasons: Season[];
  steps: AltsienSelectStep[];
  canViewPloegfiche: boolean;
}

export function WizardTeamList({ seasons, steps, canViewPloegfiche }: WizardTeamListProps) {
  const t = useTranslations("altsienSelect.wizard");
  const seasonId = useAltsienSeasonId(seasons);
  const teams = useKeyedLoad<AltsienSelectTeamSummary[]>(seasonId === null ? null : String(seasonId), () =>
    listAltsienSelectTeams(seasonId as number),
  );

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight underline">{t("title")}</h1>
          <p className="text-muted-foreground">{t("description")}</p>
        </div>
        <AltsienSeasonSelect seasons={seasons} seasonId={seasonId} />
      </div>

      {seasonId === null && <p className="text-sm text-muted-foreground">{t("noSeason")}</p>}
      {teams.isLoading && <p className="text-sm text-muted-foreground">{t("loading")}</p>}
      {teams.failed && <p className="text-sm text-destructive">{t("loadError")}</p>}
      {teams.data && teams.data.length === 0 && <p className="text-sm text-muted-foreground">{t("noTeams")}</p>}

      {teams.data && teams.data.length > 0 && seasonId !== null && (
        <div className="rounded-md border [&>div]:max-h-[65vh] [&>div]:overflow-y-auto">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="sticky top-0 z-20 bg-background font-bold underline">{t("columnTeam")}</TableHead>
                <TableHead className="sticky top-0 z-20 bg-background font-bold underline">
                  {t("columnProgress")}
                </TableHead>
                <TableHead className="sticky top-0 z-20 bg-background font-bold underline">
                  {t("columnOpenRequests")}
                </TableHead>
                <TableHead className="sticky top-0 right-0 z-30 bg-background text-right font-bold underline">
                  {t("columnActions")}
                </TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {teams.data.map((team) => {
                // Only count steps that still exist in the wizard.
                const doneCount = steps.filter((step) => team.completed_step_keys.includes(step.key)).length;
                const percent = steps.length ? Math.round((doneCount / steps.length) * 100) : 0;
                return (
                  <TableRow key={team.team_id} className="group">
                    <TableCell className="font-medium">{team.team_name}</TableCell>
                    <TableCell>
                      <div className="flex min-w-40 items-center gap-3">
                        <div
                          className="h-2 flex-1 overflow-hidden rounded-full bg-muted"
                          role="progressbar"
                          aria-valuemin={0}
                          aria-valuemax={steps.length}
                          aria-valuenow={doneCount}
                        >
                          <div
                            className={doneCount === steps.length ? "h-full bg-green-600" : "h-full bg-primary"}
                            style={{ width: `${percent}%` }}
                          />
                        </div>
                        <span className="text-sm text-muted-foreground tabular-nums">
                          {t("progressCount", { done: doneCount, total: steps.length })}
                        </span>
                      </div>
                    </TableCell>
                    <TableCell className="tabular-nums">{team.open_request_count}</TableCell>
                    <TableCell className="sticky right-0 z-10 bg-background group-hover:bg-muted/50">
                      <div className="flex justify-end gap-2">
                        <Link
                          href={`/modules/module-8/ploeg-wizard/${team.team_id}?season=${seasonId}`}
                          className={buttonVariants({ size: "sm" })}
                        >
                          <Play className="size-4" />
                          {doneCount === 0 ? t("start") : t("continue")}
                        </Link>
                        {canViewPloegfiche && (
                          <Link
                            href={`/modules/module-8/ploegfiche?season=${seasonId}&team=${team.team_id}`}
                            className={buttonVariants({ size: "sm", variant: "outline" })}
                          >
                            <FileText className="size-4" />
                            {t("ploegfiche")}
                          </Link>
                        )}
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
