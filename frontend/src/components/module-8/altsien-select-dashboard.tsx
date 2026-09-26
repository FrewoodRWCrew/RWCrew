"use client";

// Altsien Select's landing dashboard ("KPI overzicht"), styled after
// Intervention Requests' dashboard (components/module-3/
// intervention-requests-dashboard.tsx): stat tiles plus two chart panels,
// for the season chosen in the module's own season dropdown and limited to
// the teams the user can see (a Kernlid: their own teams; the organisation:
// all teams).
//
// - "Wizard progress per step" is a single-series horizontal bar chart (how
//   many teams completed each step), in the module's own fuchsia accent.
// - "Special requests per status" is a donut whose slices wear each status's
//   own admin-assigned colour (see the Request statuses screen), the same
//   reuse-the-entity's-colour treatment module-3's status donut gets.

import { CircleCheck, CircleDashed, MessageSquareText, Users, type LucideIcon } from "lucide-react";
import { useTranslations } from "next-intl";
import { Bar, BarChart, CartesianGrid, Cell, LabelList, Pie, PieChart, XAxis, YAxis } from "recharts";
import { getAltsienSelectDashboard } from "@/lib/api";
import { getModuleTheme } from "@/lib/module-theme";
import { isStatusColorKey, STATUS_COLOR_CHART_HEX } from "@/lib/status-colors";
import type { AltsienSelectDashboardStats, Season } from "@/lib/types";
import { cn } from "@/lib/utils";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import {
  type ChartConfig,
  ChartContainer,
  ChartLegend,
  ChartLegendContent,
  ChartTooltip,
  ChartTooltipContent,
} from "@/components/ui/chart";
import { AltsienSeasonSelect, useAltsienSeasonId } from "@/components/module-8/altsien-season-select";
import { useKeyedLoad } from "@/components/module-8/use-keyed-load";

interface AltsienSelectDashboardProps {
  seasons: Season[];
}

// The module accent (see module-theme.ts): fuchsia-600, lightened to
// fuchsia-400 on the dark theme — the same 600/400 pairing module-3 uses.
const MODULE_ACCENT = { light: "#c026d3", dark: "#e879f9" };
const FALLBACK_STATUS_COLOR = STATUS_COLOR_CHART_HEX.gray;

export function AltsienSelectDashboard({ seasons }: AltsienSelectDashboardProps) {
  const t = useTranslations("altsienSelect.landing");
  const seasonId = useAltsienSeasonId(seasons);

  // Reload the figures whenever another season is picked.
  const { data: stats, failed } = useKeyedLoad<AltsienSelectDashboardStats>(
    seasonId === null ? null : String(seasonId),
    () => getAltsienSelectDashboard(seasonId),
  );

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight underline">{t("title")}</h1>
          <p className="text-muted-foreground">{t("description")}</p>
        </div>
        <AltsienSeasonSelect seasons={seasons} seasonId={seasonId} />
      </div>

      {seasonId === null && <p className="text-sm text-muted-foreground">{t("noSeason")}</p>}
      {failed && <p className="text-sm text-destructive">{t("loadError")}</p>}
      {stats && <DashboardContent stats={stats} />}
    </div>
  );
}

/** The tiles and charts for one season's loaded figures. */
function DashboardContent({ stats }: { stats: AltsienSelectDashboardStats }) {
  const t = useTranslations("altsienSelect.landing");
  const tSteps = useTranslations("altsienSelect.steps");
  const { badgeClassName } = getModuleTheme("module-8");

  const statTiles: { icon: LucideIcon; label: string; value: number }[] = [
    { icon: Users, label: t("statTeams"), value: stats.total_teams },
    {
      icon: CircleCheck,
      label: t("statCompleted"),
      value: stats.completed_teams,
    },
    {
      icon: CircleDashed,
      label: t("statInProgress"),
      value: stats.in_progress_teams,
    },
    {
      icon: MessageSquareText,
      label: t("statOpenRequests"),
      value: stats.open_requests,
    },
  ];

  // Step names come from the translations when known (a newly added step
  // without a translation yet falls back to the backend's own label).
  const stepChartData = stats.step_breakdown.map((item) => ({
    label: tSteps.has(`${item.step_key}.title`) ? tSteps(`${item.step_key}.title`) : item.label,
    count: item.completed_count,
  }));
  const stepChartConfig: ChartConfig = {
    count: { label: t("chartStepsSeries"), theme: MODULE_ACCENT },
  };

  // Index-based keys, since status names aren't valid CSS variable names.
  const statusChartData = stats.status_breakdown.map((item, index) => ({
    key: `status-${index}`,
    count: item.count,
  }));
  const statusChartConfig: ChartConfig = Object.fromEntries(
    stats.status_breakdown.map((item, index) => [
      `status-${index}`,
      {
        label: item.status_name,
        theme: isStatusColorKey(item.color) ? STATUS_COLOR_CHART_HEX[item.color] : FALLBACK_STATUS_COLOR,
      },
    ]),
  );
  const isStatusChartEmpty = statusChartData.every((item) => item.count === 0);

  return (
    <>
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        {statTiles.map(({ icon: Icon, label, value }) => (
          <Card key={label}>
            <CardContent className="flex flex-col items-center gap-2 text-center">
              <div className={cn("flex size-10 items-center justify-center rounded-full", badgeClassName)}>
                <Icon className="size-5" aria-hidden="true" />
              </div>
              <span className="text-2xl font-semibold tabular-nums">{value.toLocaleString()}</span>
              <span className="text-xs text-muted-foreground">{label}</span>
            </CardContent>
          </Card>
        ))}
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>{t("chartStepsTitle")}</CardTitle>
            <CardDescription>{t("chartStepsDescription", { total: stats.total_teams })}</CardDescription>
          </CardHeader>
          <CardContent>
            {stats.total_teams === 0 ? (
              <p className="flex h-64 items-center justify-center text-center text-sm text-muted-foreground">
                {t("noTeams")}
              </p>
            ) : (
              <ChartContainer config={stepChartConfig} className="max-h-64 w-full">
                <BarChart data={stepChartData} layout="vertical" margin={{ left: 8, right: 32 }}>
                  <CartesianGrid horizontal={false} />
                  <XAxis type="number" hide allowDecimals={false} domain={[0, stats.total_teams]} />
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
            <CardTitle>{t("chartStatusTitle")}</CardTitle>
            <CardDescription>{t("chartStatusDescription")}</CardDescription>
          </CardHeader>
          <CardContent>
            {isStatusChartEmpty ? (
              <p className="flex h-64 items-center justify-center text-center text-sm text-muted-foreground">
                {t("chartStatusEmpty")}
              </p>
            ) : (
              <ChartContainer config={statusChartConfig} className="mx-auto aspect-square max-h-64">
                <PieChart>
                  <ChartTooltip content={<ChartTooltipContent hideLabel nameKey="key" />} />
                  <Pie
                    data={statusChartData}
                    dataKey="count"
                    nameKey="key"
                    innerRadius={48}
                    outerRadius={80}
                    strokeWidth={2}
                  >
                    {statusChartData.map((entry) => (
                      <Cell key={entry.key} fill={`var(--color-${entry.key})`} stroke="var(--background)" />
                    ))}
                  </Pie>
                  <ChartLegend content={<ChartLegendContent nameKey="key" />} />
                </PieChart>
              </ChartContainer>
            )}
          </CardContent>
        </Card>
      </div>
    </>
  );
}
