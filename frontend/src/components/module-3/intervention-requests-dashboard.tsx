"use client";

// Intervention Requests' landing dashboard ("KPI overview"): 3 stat tiles +
// 2 chart panels, styled after MasterData's and TagScan's own dashboards
// (components/module-9/masterdata-dashboard.tsx,
// components/module-1/tag-dashboard.tsx).
//
// The status donut's slice colours come from STATUS_COLOR_CHART_HEX, i.e.
// each status's own admin-assigned colour (see the Intervention Statuses
// screen) — the same colour already used to tint that status's rows on the
// Intervention Requests screen. This isn't a fresh categorical palette
// being picked here (which the dataviz skill's validator would apply to),
// it's an existing, already-shipped per-entity colour reused for
// consistency, exactly like the row highlighting does. Chart config keys
// are index-based ("status-0", "status-1", ...) rather than the status
// name itself, since a status name can contain spaces/punctuation that
// isn't a valid CSS custom-property name (ChartContainer emits one
// `--color-<key>` variable per config key — see ui/chart.tsx).
//
// The team breakdown is a single-series bar chart in module-3's own accent
// colour, the same treatment MasterData's/TagScan's single-series charts
// get — only teams/names that actually have at least one request appear,
// same idea as TagScan's "top products" breakdown.

import { Boxes, CircleDot, CircleCheck, type LucideIcon } from "lucide-react";
import { useTranslations } from "next-intl";
import { Bar, BarChart, CartesianGrid, Cell, LabelList, Pie, PieChart, XAxis, YAxis } from "recharts";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import {
  type ChartConfig,
  ChartContainer,
  ChartLegend,
  ChartLegendContent,
  ChartTooltip,
  ChartTooltipContent,
} from "@/components/ui/chart";
import { getModuleTheme } from "@/lib/module-theme";
import { isStatusColorKey, STATUS_COLOR_CHART_HEX } from "@/lib/status-colors";
import { cn } from "@/lib/utils";
import type { InterventionRequestsDashboardStats } from "@/lib/types";

interface InterventionRequestsDashboardProps {
  stats: InterventionRequestsDashboardStats;
}

const MODULE_ACCENT = { light: "#ea580c", dark: "#fb923c" };
const FALLBACK_STATUS_COLOR = STATUS_COLOR_CHART_HEX.gray;

export function InterventionRequestsDashboard({ stats }: InterventionRequestsDashboardProps) {
  const t = useTranslations("interventionRequests.landing");
  const { badgeClassName } = getModuleTheme("module-3");

  const statTiles: { icon: LucideIcon; label: string; value: number }[] = [
    { icon: Boxes, label: t("statTotalRequests"), value: stats.total_requests },
    { icon: CircleDot, label: t("statOpenRequests"), value: stats.open_requests },
    { icon: CircleCheck, label: t("statClosedRequests"), value: stats.closed_requests },
  ];

  const statusChartData = stats.status_breakdown.map((item, index) => ({
    key: `status-${index}`,
    name: item.status_name,
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

  const teamChartData = stats.team_breakdown.map((item) => ({
    label: item.team_name,
    count: item.count,
  }));
  const teamChartConfig: ChartConfig = { count: { label: t("chartTeamSeries"), theme: MODULE_ACCENT } };

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">{t("title")}</h1>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
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
            <CardTitle>{t("chartStatusTitle")}</CardTitle>
            <CardDescription>{t("chartStatusDescription")}</CardDescription>
          </CardHeader>
          <CardContent>
            {isStatusChartEmpty ? (
              <p className="flex h-64 items-center justify-center text-center text-sm text-muted-foreground">
                {t("chartEmpty")}
              </p>
            ) : (
              <ChartContainer config={statusChartConfig} className="mx-auto aspect-square max-h-64">
                <PieChart>
                  <ChartTooltip content={<ChartTooltipContent hideLabel nameKey="key" />} />
                  <Pie data={statusChartData} dataKey="count" nameKey="key" innerRadius={48} outerRadius={80} strokeWidth={2}>
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

        <Card>
          <CardHeader>
            <CardTitle>{t("chartTeamTitle")}</CardTitle>
            <CardDescription>{t("chartTeamDescription")}</CardDescription>
          </CardHeader>
          <CardContent>
            {teamChartData.length === 0 ? (
              <p className="flex h-64 items-center justify-center text-center text-sm text-muted-foreground">
                {t("chartEmpty")}
              </p>
            ) : (
              <ChartContainer config={teamChartConfig} className="max-h-64 w-full">
                <BarChart data={teamChartData} layout="vertical" margin={{ left: 8, right: 24 }}>
                  <CartesianGrid horizontal={false} />
                  <XAxis type="number" hide allowDecimals={false} />
                  <YAxis dataKey="label" type="category" tickLine={false} axisLine={false} width={110} />
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
    </div>
  );
}
