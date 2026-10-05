"use client";

// StockMaster's main page ("KPI"), styled like the other modules' KPI
// dashboards (e.g. components/module-8/altsien-select-dashboard.tsx): stat
// tiles at the top — each linking to the screen behind it — and three
// charts for the season chosen in the module's own season dropdown:
// - bookings per month, stacked per action (in process order);
// - consumption per team (what didn't come back from the kar trips);
// - the ten most consumed products (trips + "Uitboeken").

import {
  Boxes,
  ClipboardList,
  PackageCheck,
  ShoppingCart,
  Truck,
  TriangleAlert,
  Warehouse,
  type LucideIcon,
} from "lucide-react";
import { useTranslations } from "next-intl";
import { Bar, BarChart, CartesianGrid, LabelList, XAxis, YAxis } from "recharts";
import { Link } from "@/i18n/navigation";
import { getStockMasterDashboard } from "@/lib/api";
import { getModuleTheme } from "@/lib/module-theme";
import type { Season, StockMasterDashboard as DashboardStats } from "@/lib/types";
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
import { useKeyedLoad } from "@/components/module-4/use-keyed-load";
import { StockMasterSeasonSelect, useStockMasterSeasonId } from "@/components/module-4/stockmaster-season-select";
import { ACTION_ORDER, STOCKMASTER_BASE } from "@/components/module-4/stockmaster-common";

interface StockMasterDashboardProps {
  seasons: Season[];
}

// The module accent (teal-600, lightened to teal-400 on the dark theme).
const MODULE_ACCENT = { light: "#0d9488", dark: "#2dd4bf" };

// One colour per action for the stacked monthly bars (process order).
const ACTION_COLORS: Record<string, { light: string; dark: string }> = {
  book_in: { light: "#0d9488", dark: "#2dd4bf" },
  kar_load: { light: "#2563eb", dark: "#60a5fa" },
  book_out: { light: "#dc2626", dark: "#f87171" },
  kar_dispatch: { light: "#ea580c", dark: "#fb923c" },
  kar_return: { light: "#16a34a", dark: "#4ade80" },
  kar_unload: { light: "#9333ea", dark: "#c084fc" },
  count: { light: "#4b5563", dark: "#9ca3af" },
};

export function StockMasterDashboard({ seasons }: StockMasterDashboardProps) {
  const t = useTranslations("stockMaster.kpi");
  const seasonId = useStockMasterSeasonId(seasons);

  // Reload the figures whenever another season is picked.
  const { data: stats, failed } = useKeyedLoad<DashboardStats>(
    seasonId === null ? null : String(seasonId),
    () => getStockMasterDashboard(seasonId as number),
  );

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight underline">{t("title")}</h1>
          <p className="text-muted-foreground">{t("description")}</p>
        </div>
        <StockMasterSeasonSelect seasons={seasons} seasonId={seasonId} />
      </div>

      {seasonId === null && <p className="text-sm text-muted-foreground">{t("noSeason")}</p>}
      {failed && <p className="text-sm text-destructive">{t("loadError")}</p>}
      {stats && <DashboardContent stats={stats} seasonId={seasonId} />}
    </div>
  );
}

/** The tiles and charts for one season's loaded figures. */
function DashboardContent({ stats, seasonId }: { stats: DashboardStats; seasonId: number | null }) {
  const t = useTranslations("stockMaster.kpi");
  const tTypes = useTranslations("stockMaster.docTypes");
  const { badgeClassName } = getModuleTheme("module-4");
  const seasonQuery = seasonId ? `?season=${seasonId}` : "";

  const tiles: { icon: LucideIcon; label: string; value: string; href: string; warn?: boolean }[] = [
    { icon: Boxes, label: t("tileTotal"), value: stats.total_stock.toLocaleString(), href: `${STOCKMASTER_BASE}/stock` },
    { icon: Warehouse, label: t("tileFree"), value: stats.free_stock.toLocaleString(), href: `${STOCKMASTER_BASE}/stock` },
    { icon: PackageCheck, label: t("tileInKars"), value: stats.in_kars.toLocaleString(), href: `${STOCKMASTER_BASE}/kars${seasonQuery}` },
    {
      icon: Truck,
      label: t("tileKars"),
      value: `${stats.kars_in_warehouse} / ${stats.kars_out}`,
      href: `${STOCKMASTER_BASE}/kars${seasonQuery}`,
    },
    {
      icon: ClipboardList,
      label: t("tileComplete"),
      value: `${stats.kars_complete} / ${stats.kars_with_needs}`,
      href: `${STOCKMASTER_BASE}/requirements${seasonQuery}`,
    },
    {
      icon: TriangleAlert,
      label: t("tileBelowMinimum"),
      value: String(stats.below_minimum),
      href: `${STOCKMASTER_BASE}/stock?below=1`,
      warn: stats.below_minimum > 0,
    },
    {
      icon: ShoppingCart,
      label: t("tileToOrder"),
      value: String(stats.order_lines),
      href: `${STOCKMASTER_BASE}/order-needs${seasonQuery}`,
      warn: stats.order_lines > 0,
    },
  ];

  // Monthly bookings: one row per month, one column per action.
  const months = [...new Set(stats.bookings_per_month.map((item) => item.month))].sort();
  const monthData = months.map((month) => {
    const row: Record<string, string | number> = { month };
    for (const item of stats.bookings_per_month.filter((entry) => entry.month === month)) {
      row[item.doc_type] = item.count;
    }
    return row;
  });
  const usedActions = ACTION_ORDER.filter((action) => stats.bookings_per_month.some((item) => item.doc_type === action));
  const monthConfig: ChartConfig = Object.fromEntries(
    usedActions.map((action) => [action, { label: tTypes(action), theme: ACTION_COLORS[action] }]),
  );

  const quantityConfig: ChartConfig = { quantity: { label: t("pieces"), theme: MODULE_ACCENT } };

  return (
    <>
      <div className="grid grid-cols-2 gap-4 md:grid-cols-4 xl:grid-cols-7">
        {tiles.map(({ icon: Icon, label, value, href, warn }) => (
          <Link key={label} href={href} className="rounded-xl focus-visible:ring-2 focus-visible:ring-ring">
            <Card className="h-full transition-colors hover:bg-muted/40">
              <CardContent className="flex flex-col items-center gap-2 text-center">
                <div
                  className={cn(
                    "flex size-10 items-center justify-center rounded-full",
                    warn ? "bg-orange-100 text-orange-700 dark:bg-orange-500/15 dark:text-orange-300" : badgeClassName,
                  )}
                >
                  <Icon className="size-5" aria-hidden="true" />
                </div>
                <span className="text-2xl font-semibold tabular-nums">{value}</span>
                <span className="text-xs text-muted-foreground">{label}</span>
              </CardContent>
            </Card>
          </Link>
        ))}
      </div>

      <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
        <Card className="xl:col-span-2">
          <CardHeader>
            <CardTitle>{t("chartMonthsTitle")}</CardTitle>
            <CardDescription>{t("chartMonthsDescription")}</CardDescription>
          </CardHeader>
          <CardContent>
            {monthData.length === 0 ? (
              <p className="flex h-48 items-center justify-center text-sm text-muted-foreground">{t("noBookings")}</p>
            ) : (
              <ChartContainer config={monthConfig} className="max-h-72 w-full">
                <BarChart data={monthData} margin={{ left: 8, right: 8 }}>
                  <CartesianGrid vertical={false} />
                  <XAxis dataKey="month" tickLine={false} axisLine={false} />
                  <YAxis allowDecimals={false} tickLine={false} axisLine={false} width={32} />
                  <ChartTooltip content={<ChartTooltipContent />} />
                  <ChartLegend content={<ChartLegendContent />} />
                  {usedActions.map((action, index) => (
                    <Bar
                      key={action}
                      dataKey={action}
                      stackId="bookings"
                      fill={`var(--color-${action})`}
                      radius={index === usedActions.length - 1 ? [4, 4, 0, 0] : 0}
                    />
                  ))}
                </BarChart>
              </ChartContainer>
            )}
          </CardContent>
        </Card>

        <QuantityChart
          title={t("chartTeamsTitle")}
          description={t("chartTeamsDescription")}
          data={stats.consumption_per_team}
          config={quantityConfig}
          empty={t("noConsumption")}
        />
        <QuantityChart
          title={t("chartProductsTitle")}
          description={t("chartProductsDescription")}
          data={stats.top_consumed_products}
          config={quantityConfig}
          empty={t("noConsumption")}
        />
      </div>
    </>
  );
}

/** A horizontal bar chart of names with a number of pieces. */
function QuantityChart({
  title,
  description,
  data,
  config,
  empty,
}: {
  title: string;
  description: string;
  data: { name: string; quantity: number }[];
  config: ChartConfig;
  empty: string;
}) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
        <CardDescription>{description}</CardDescription>
      </CardHeader>
      <CardContent>
        {data.length === 0 ? (
          <p className="flex h-48 items-center justify-center text-center text-sm text-muted-foreground">{empty}</p>
        ) : (
          <ChartContainer config={config} className="max-h-72 w-full">
            <BarChart data={data} layout="vertical" margin={{ left: 8, right: 32 }}>
              <CartesianGrid horizontal={false} />
              <XAxis type="number" hide allowDecimals={false} />
              <YAxis dataKey="name" type="category" tickLine={false} axisLine={false} width={140} />
              <ChartTooltip content={<ChartTooltipContent />} />
              <Bar dataKey="quantity" fill="var(--color-quantity)" radius={4} barSize={18}>
                <LabelList dataKey="quantity" position="right" className="fill-foreground text-xs" />
              </Bar>
            </BarChart>
          </ChartContainer>
        )}
      </CardContent>
    </Card>
  );
}
