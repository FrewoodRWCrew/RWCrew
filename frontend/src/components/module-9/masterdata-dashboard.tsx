"use client";

// MasterData's landing dashboard ("Masterdata Overview"): 6 stat tiles +
// 3 chart panels, styled after TagScan's own dashboard
// (components/module-1/tag-dashboard.tsx). Unlike TagScan, none of the
// masterdata models have a timestamp column, so there's no time-series
// chart here — instead all 3 charts are horizontal bar breakdowns
// (by Type/Category/Warehouse), single-series in MasterData's own module
// accent colour, the same treatment TagScan's own "Top products by tag
// count" bar chart uses (a dynamic, open-ended list rather than a fixed
// enum, so — unlike the fixed 5-slice status donut — no categorical
// palette validation is needed here).

import {
  Ban,
  CalendarDays,
  Package,
  Recycle,
  Truck,
  TriangleAlert,
  type LucideIcon,
} from "lucide-react";
import { useTranslations } from "next-intl";
import { Bar, BarChart, CartesianGrid, LabelList, XAxis, YAxis } from "recharts";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { type ChartConfig, ChartContainer, ChartTooltip, ChartTooltipContent } from "@/components/ui/chart";
import { getModuleTheme } from "@/lib/module-theme";
import { cn } from "@/lib/utils";
import type { MasterDataDashboardStats } from "@/lib/types";

interface MasterDataDashboardProps {
  stats: MasterDataDashboardStats;
}

const MODULE_ACCENT = { light: "#0891b2", dark: "#22d3ee" };

export function MasterDataDashboard({ stats }: MasterDataDashboardProps) {
  const t = useTranslations("masterdata.landing");
  const { badgeClassName } = getModuleTheme("module-9");

  const statTiles: { icon: LucideIcon; label: string; value: number }[] = [
    { icon: Package, label: t("statTotalProducts"), value: stats.total_products },
    { icon: CalendarDays, label: t("statTotalSeasons"), value: stats.total_seasons },
    { icon: Ban, label: t("statBlockedProducts"), value: stats.blocked_products },
    { icon: Recycle, label: t("statConsumableProducts"), value: stats.consumable_products },
    { icon: Truck, label: t("statLogisticsProducts"), value: stats.logistics_products },
    { icon: TriangleAlert, label: t("statMissingClassification"), value: stats.products_missing_classification },
  ];

  const typeChartData = stats.products_by_type.map((item) => ({
    label: item.type_name ?? t("unassignedLabel"),
    count: item.count,
  }));
  const categoryChartData = stats.products_by_category.map((item) => ({
    label: item.category_name ?? t("unassignedLabel"),
    count: item.count,
  }));
  const warehouseChartData = stats.products_by_warehouse.map((item) => ({
    label: item.warehouse_name ?? t("unassignedLabel"),
    count: item.count,
  }));

  const typeChartConfig: ChartConfig = { count: { label: t("chartTypeSeries"), theme: MODULE_ACCENT } };
  const categoryChartConfig: ChartConfig = { count: { label: t("chartCategorySeries"), theme: MODULE_ACCENT } };
  const warehouseChartConfig: ChartConfig = { count: { label: t("chartWarehouseSeries"), theme: MODULE_ACCENT } };

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
        <BreakdownBarChart
          title={t("chartTypeTitle")}
          description={t("chartTypeDescription")}
          emptyMessage={t("chartEmpty")}
          data={typeChartData}
          config={typeChartConfig}
        />
        <BreakdownBarChart
          title={t("chartCategoryTitle")}
          description={t("chartCategoryDescription")}
          emptyMessage={t("chartEmpty")}
          data={categoryChartData}
          config={categoryChartConfig}
        />
        <BreakdownBarChart
          title={t("chartWarehouseTitle")}
          description={t("chartWarehouseDescription")}
          emptyMessage={t("chartEmpty")}
          data={warehouseChartData}
          config={warehouseChartConfig}
        />
      </div>
    </div>
  );
}

interface BreakdownBarChartProps {
  title: string;
  description: string;
  emptyMessage: string;
  data: { label: string; count: number }[];
  config: ChartConfig;
}

/** One horizontal bar-chart card, shared by the 3 breakdown charts above —
 * they only differ in their data/labels, not their shape.
 */
function BreakdownBarChart({ title, description, emptyMessage, data, config }: BreakdownBarChartProps) {
  // A dashboard with zero products anywhere still has one "Unassigned"
  // entry (count 0) from the backend's zero-fill — treat that as "empty"
  // too, rather than showing a single, meaningless zero-length bar.
  const isEmpty = data.every((item) => item.count === 0);

  return (
    <Card>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
        <CardDescription>{description}</CardDescription>
      </CardHeader>
      <CardContent>
        {isEmpty ? (
          <p className="flex h-64 items-center justify-center text-center text-sm text-muted-foreground">
            {emptyMessage}
          </p>
        ) : (
          <ChartContainer config={config} className="max-h-64 w-full">
            <BarChart data={data} layout="vertical" margin={{ left: 8, right: 24 }}>
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
  );
}
