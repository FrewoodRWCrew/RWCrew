"use client";

// KarTracker's landing dashboard ("KPI Overview"), styled after Altsien
// Select's and Intervention Requests' dashboards
// (components/module-8/altsien-select-dashboard.tsx,
// components/module-3/intervention-requests-dashboard.tsx): stat tiles plus
// four chart panels.
//
// - The fleet (karren per status, karren per team) and the movement log
//   (per day, last 14 days) don't depend on a season.
// - The "Plan a kar" tile and chart follow the season picked in the header —
//   the same selector the Plan a kar screen itself uses — and show a hint
//   when no season is selected.
//
// Every chart is a single series, so they all wear the module's own purple
// accent (see module-theme.ts). Kar statuses have no admin-assigned colour
// (unlike module-3's/module-8's statuses), hence bars instead of a donut.

import { CalendarCheck, Container, Route, Unlink, Users, type LucideIcon } from "lucide-react";
import { useFormatter, useTranslations } from "next-intl";
import { Bar, BarChart, CartesianGrid, LabelList, XAxis, YAxis } from "recharts";
import { getKarTrackerDashboard } from "@/lib/api";
import { getModuleTheme } from "@/lib/module-theme";
import type { KarTrackerDashboardStats } from "@/lib/types";
import { cn } from "@/lib/utils";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { type ChartConfig, ChartContainer, ChartTooltip, ChartTooltipContent } from "@/components/ui/chart";
import { useKeyedLoad } from "@/components/module-8/use-keyed-load";
import { useSelectedSeason } from "@/components/shared/season-provider";

// The module accent (see module-theme.ts): purple-600, lightened to
// purple-400 on the dark theme — the same 600/400 pairing the other
// dashboards use.
const MODULE_ACCENT = { light: "#9333ea", dark: "#c084fc" };

export function KarTrackerDashboard() {
  const t = useTranslations("karTracker.landing");
  const { selectedSeasonId } = useSelectedSeason();

  // The key always exists (the fleet figures need no season), and changes
  // whenever another season is picked in the header, which reloads.
  const { data: stats, failed } = useKeyedLoad<KarTrackerDashboardStats>(
    `season:${selectedSeasonId ?? "none"}`,
    () => getKarTrackerDashboard(selectedSeasonId),
  );

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight underline">{t("title")}</h1>
        <p className="text-muted-foreground">{t("description")}</p>
      </div>

      {failed && <p className="text-sm text-destructive">{t("loadError")}</p>}
      {stats && <DashboardContent stats={stats} />}
    </div>
  );
}

/** A chart panel's "nothing to draw" message, the same height as a chart. */
function EmptyChart({ message }: { message: string }) {
  return (
    <p className="flex h-64 items-center justify-center text-center text-sm text-muted-foreground">{message}</p>
  );
}

/** The tiles and charts for one set of loaded figures. */
function DashboardContent({ stats }: { stats: KarTrackerDashboardStats }) {
  const t = useTranslations("karTracker.landing");
  const format = useFormatter();
  const { badgeClassName } = getModuleTheme("module-2");

  // Plan a kar is only known for a chosen season; shown as "planned / expected".
  const hasSeason = stats.plan_kar_planned !== null && stats.plan_kar_expected !== null;
  const statTiles: { icon: LucideIcon; label: string; value: string }[] = [
    { icon: Container, label: t("statTotalKarren"), value: stats.total_karren.toLocaleString() },
    { icon: Users, label: t("statWithTeam"), value: stats.karren_with_team.toLocaleString() },
    { icon: Unlink, label: t("statWithoutTeam"), value: stats.karren_without_team.toLocaleString() },
    { icon: Route, label: t("statMovements"), value: stats.movements_last_7_days.toLocaleString() },
    {
      icon: CalendarCheck,
      label: hasSeason ? t("statPlanKar") : t("statPlanKarNoSeason"),
      value: hasSeason
        ? `${stats.plan_kar_planned!.toLocaleString()} / ${stats.plan_kar_expected!.toLocaleString()}`
        : "–",
    },
  ];

  // All four charts share one series config shape: a single accent-coloured count.
  const karrenConfig: ChartConfig = { count: { label: t("chartKarrenSeries"), theme: MODULE_ACCENT } };
  const movementsConfig: ChartConfig = { count: { label: t("chartMovementsSeries"), theme: MODULE_ACCENT } };
  const planKarConfig: ChartConfig = { count: { label: t("chartPlanKarSeries"), theme: MODULE_ACCENT } };

  const statusChartData = stats.status_breakdown.map((item) => ({ label: item.status_name, count: item.count }));
  const teamChartData = stats.team_breakdown.map((item) => ({ label: item.team_name, count: item.count }));
  // Days arrive as UTC ISO dates; format them in UTC too so they never shift a day.
  const movementChartData = stats.movements_per_day.map((item) => ({
    label: format.dateTime(new Date(`${item.day}T00:00:00Z`), { day: "numeric", month: "short", timeZone: "UTC" }),
    count: item.count,
  }));
  const planKarChartData = (stats.festival_plan_breakdown ?? []).map((item) => ({
    label: item.festival_name,
    count: item.planned_teams,
  }));

  // A horizontal bar chart grows with its number of rows, so long team or
  // festival lists stay readable instead of squashing into a fixed height.
  const rowsHeight = (rows: number) => ({ height: Math.max(160, rows * 32 + 24) });

  return (
    <>
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-5">
        {statTiles.map(({ icon: Icon, label, value }) => (
          <Card key={label}>
            <CardContent className="flex flex-col items-center gap-2 text-center">
              <div className={cn("flex size-10 items-center justify-center rounded-full", badgeClassName)}>
                <Icon className="size-5" aria-hidden="true" />
              </div>
              <span className="text-2xl font-semibold tabular-nums">{value}</span>
              <span className="text-xs text-muted-foreground">{label}</span>
            </CardContent>
          </Card>
        ))}
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>{t("chartStatusTitle")}</CardTitle>
            <CardDescription>{t("chartStatusDescription")}</CardDescription>
          </CardHeader>
          <CardContent>
            {statusChartData.length === 0 ? (
              <EmptyChart message={t("chartStatusEmpty")} />
            ) : (
              <ChartContainer config={karrenConfig} className="w-full" style={rowsHeight(statusChartData.length)}>
                <BarChart data={statusChartData} layout="vertical" margin={{ left: 8, right: 32 }}>
                  <CartesianGrid horizontal={false} />
                  <XAxis type="number" hide allowDecimals={false} />
                  <YAxis dataKey="label" type="category" tickLine={false} axisLine={false} width={130} />
                  <ChartTooltip content={<ChartTooltipContent />} />
                  <Bar dataKey="count" fill="var(--color-count)" radius={4} barSize={20}>
                    <LabelList dataKey="count" position="right" className="fill-foreground text-xs" />
                  </Bar>
                </BarChart>
              </ChartContainer>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>{t("chartTeamTitle")}</CardTitle>
            <CardDescription>{t("chartTeamDescription")}</CardDescription>
          </CardHeader>
          <CardContent>
            {teamChartData.length === 0 ? (
              <EmptyChart message={t("chartTeamEmpty")} />
            ) : (
              <ChartContainer config={karrenConfig} className="w-full" style={rowsHeight(teamChartData.length)}>
                <BarChart data={teamChartData} layout="vertical" margin={{ left: 8, right: 32 }}>
                  <CartesianGrid horizontal={false} />
                  <XAxis type="number" hide allowDecimals={false} />
                  <YAxis dataKey="label" type="category" tickLine={false} axisLine={false} width={130} />
                  <ChartTooltip content={<ChartTooltipContent />} />
                  <Bar dataKey="count" fill="var(--color-count)" radius={4} barSize={20}>
                    <LabelList dataKey="count" position="right" className="fill-foreground text-xs" />
                  </Bar>
                </BarChart>
              </ChartContainer>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>{t("chartMovementsTitle")}</CardTitle>
            <CardDescription>{t("chartMovementsDescription")}</CardDescription>
          </CardHeader>
          <CardContent>
            {/* Always 14 zero-filled days, so there's no empty state: a flat chart says "quiet". */}
            <ChartContainer config={movementsConfig} className="h-64 w-full">
              <BarChart data={movementChartData} margin={{ top: 20 }}>
                <CartesianGrid vertical={false} />
                <XAxis dataKey="label" tickLine={false} axisLine={false} interval="preserveStartEnd" />
                <YAxis hide allowDecimals={false} />
                <ChartTooltip content={<ChartTooltipContent />} />
                <Bar dataKey="count" fill="var(--color-count)" radius={4}>
                  <LabelList dataKey="count" position="top" className="fill-foreground text-xs" />
                </Bar>
              </BarChart>
            </ChartContainer>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>{t("chartPlanKarTitle")}</CardTitle>
            {hasSeason && (
              <CardDescription>{t("chartPlanKarDescription", { total: stats.active_teams ?? 0 })}</CardDescription>
            )}
          </CardHeader>
          <CardContent>
            {!hasSeason ? (
              <EmptyChart message={t("chartPlanKarNoSeason")} />
            ) : planKarChartData.length === 0 ? (
              <EmptyChart message={t("chartPlanKarEmpty")} />
            ) : (
              <ChartContainer config={planKarConfig} className="w-full" style={rowsHeight(planKarChartData.length)}>
                <BarChart data={planKarChartData} layout="vertical" margin={{ left: 8, right: 32 }}>
                  <CartesianGrid horizontal={false} />
                  {/* Scaled to the number of active teams, so a full bar means "every team planned". */}
                  <XAxis type="number" hide allowDecimals={false} domain={[0, Math.max(stats.active_teams ?? 0, 1)]} />
                  <YAxis dataKey="label" type="category" tickLine={false} axisLine={false} width={130} />
                  <ChartTooltip content={<ChartTooltipContent />} />
                  <Bar dataKey="count" fill="var(--color-count)" radius={4} barSize={20}>
                    <LabelList dataKey="count" position="right" className="fill-foreground text-xs" />
                  </Bar>
                </BarChart>
              </ChartContainer>
            )}
          </CardContent>
        </Card>
      </div>
    </>
  );
}
