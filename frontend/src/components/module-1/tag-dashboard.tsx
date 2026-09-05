"use client";

// TagScan's landing dashboard: 6 stat tiles + 3 chart panels, styled
// after a reference KPI-dashboard mockup (bordered stat cards in a row,
// bordered chart cards below). Colour comes from two sources:
//
// - The single-series charts (Registrations over time, Top Products) and
//   every stat tile's icon badge reuse TagScan's own module accent (see
//   module-theme.ts / the landing tile) — MODULE_ACCENT below, so this
//   page can never visually drift from TagScan's tile everywhere else in
//   the app.
// - The 5-slice "Tags by Status" donut is a real categorical breakdown
//   (5 distinct identities, not one series), so it uses the dataviz
//   skill's validated 8-hue categorical palette instead of a single hue —
//   a monochrome-blue donut would fail the CVD/distinguishability checks
//   for a 5-way breakdown. STATUS_COLORS below is fixed forever (never
//   reassigned by filter/rank) and was run through
//   dataviz/scripts/validate_palette.js for both light and dark mode,
//   including the donut ring's wrap-around pair (slot 5 next to slot 1) —
//   all checks pass; light mode carries a contrast WARN on 3 of the 5
//   hues, mitigated here by the always-visible legend (never color alone).

import {
  Boxes,
  CalendarPlus,
  Inbox,
  Link2,
  TriangleAlert,
  Unlink2,
  type LucideIcon,
} from "lucide-react";
import { useTranslations } from "next-intl";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  LabelList,
  Pie,
  PieChart,
  XAxis,
  YAxis,
} from "recharts";
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
import { cn } from "@/lib/utils";
import type { RfidTagStatus, TagDashboardStats } from "@/lib/types";

interface TagDashboardProps {
  stats: TagDashboardStats;
}

const MODULE_ACCENT = { light: "#2563eb", dark: "#60a5fa" };

const STATUS_COLORS: Record<RfidTagStatus, { light: string; dark: string }> = {
  active: { light: "#2a78d6", dark: "#3987e5" },
  inactive: { light: "#eb6834", dark: "#d95926" },
  lost: { light: "#1baf7a", dark: "#199e70" },
  damaged: { light: "#eda100", dark: "#c98500" },
  retired: { light: "#e87ba4", dark: "#d55181" },
};

/** "2026-01-05" -> "01-05" — deterministic, no locale/timezone dependence
 * (see tag-management.tsx's formatDate for why toLocaleDateString() is
 * avoided: it causes a server/client hydration mismatch).
 */
function formatWeekLabel(weekStart: string): string {
  return weekStart.slice(5);
}

export function TagDashboard({ stats }: TagDashboardProps) {
  const t = useTranslations("tagscan.landing");
  const tStatus = useTranslations("tagscan.tagManagement.status");
  const { badgeClassName } = getModuleTheme("module-1");

  const statTiles: { icon: LucideIcon; label: string; value: number }[] = [
    { icon: Boxes, label: t("statTotalTags"), value: stats.total_tags },
    { icon: Inbox, label: t("statUnreadedTags"), value: stats.unreaded_tags_count },
    { icon: Link2, label: t("statAssignedTags"), value: stats.assigned_tags },
    { icon: Unlink2, label: t("statUnassignedTags"), value: stats.unassigned_tags },
    { icon: TriangleAlert, label: t("statLostDamagedTags"), value: stats.lost_or_damaged_tags },
    { icon: CalendarPlus, label: t("statRegisteredThisMonth"), value: stats.registered_this_month },
  ];

  const statusChartData = stats.status_breakdown.map((item) => ({
    status: item.status,
    count: item.count,
  }));
  const statusChartConfig: ChartConfig = Object.fromEntries(
    stats.status_breakdown.map((item) => [item.status, { label: tStatus(item.status), theme: STATUS_COLORS[item.status] }]),
  );

  const registrationsChartData = stats.registrations_by_week.map((item) => ({
    week: formatWeekLabel(item.week_start),
    count: item.count,
  }));
  const registrationsChartConfig: ChartConfig = {
    count: { label: t("chartRegistrationsSeries"), theme: MODULE_ACCENT },
  };

  const topProductsChartData = stats.top_products.map((item) => ({
    product: item.product_name,
    count: item.tag_count,
  }));
  const topProductsChartConfig: ChartConfig = {
    count: { label: t("chartTopProductsSeries"), theme: MODULE_ACCENT },
  };

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">{t("title")}</h1>
      </div>

      <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-6">
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

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <Card>
          <CardHeader>
            <CardTitle>{t("chartStatusTitle")}</CardTitle>
            <CardDescription>{t("chartStatusDescription")}</CardDescription>
          </CardHeader>
          <CardContent>
            <ChartContainer config={statusChartConfig} className="mx-auto aspect-square max-h-64">
              <PieChart>
                <ChartTooltip content={<ChartTooltipContent hideLabel nameKey="status" />} />
                <Pie data={statusChartData} dataKey="count" nameKey="status" innerRadius={48} outerRadius={80} strokeWidth={2}>
                  {statusChartData.map((entry) => (
                    <Cell key={entry.status} fill={`var(--color-${entry.status})`} stroke="var(--background)" />
                  ))}
                </Pie>
                <ChartLegend content={<ChartLegendContent nameKey="status" />} />
              </PieChart>
            </ChartContainer>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>{t("chartRegistrationsTitle")}</CardTitle>
            <CardDescription>{t("chartRegistrationsDescription")}</CardDescription>
          </CardHeader>
          <CardContent>
            <ChartContainer config={registrationsChartConfig} className="max-h-64 w-full">
              <AreaChart data={registrationsChartData} margin={{ left: 8, right: 8 }}>
                <CartesianGrid vertical={false} />
                <XAxis dataKey="week" tickLine={false} axisLine={false} tickMargin={8} />
                <YAxis tickLine={false} axisLine={false} width={32} allowDecimals={false} />
                <ChartTooltip content={<ChartTooltipContent />} />
                <Area
                  dataKey="count"
                  type="monotone"
                  fill="var(--color-count)"
                  fillOpacity={0.1}
                  stroke="var(--color-count)"
                  strokeWidth={2}
                />
              </AreaChart>
            </ChartContainer>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>{t("chartTopProductsTitle")}</CardTitle>
            <CardDescription>{t("chartTopProductsDescription")}</CardDescription>
          </CardHeader>
          <CardContent>
            {topProductsChartData.length === 0 ? (
              <p className="flex h-64 items-center justify-center text-center text-sm text-muted-foreground">
                {t("chartTopProductsEmpty")}
              </p>
            ) : (
              <ChartContainer config={topProductsChartConfig} className="max-h-64 w-full">
                <BarChart data={topProductsChartData} layout="vertical" margin={{ left: 8, right: 24 }}>
                  <CartesianGrid horizontal={false} />
                  <XAxis type="number" hide allowDecimals={false} />
                  <YAxis dataKey="product" type="category" tickLine={false} axisLine={false} width={110} />
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
