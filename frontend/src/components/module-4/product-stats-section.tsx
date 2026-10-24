"use client";

// The "Producten" section of StockMaster's KPI page (moved here from
// MasterData's dashboard together with the product screens): five stat
// tiles and three horizontal bar breakdowns (by Type/Categorie/Magazijn),
// for all products — not per season, so it ignores the season dropdown.
// Every tile opens the Products screen when the user may see it.

import { Ban, Package, Recycle, Truck, TriangleAlert, type LucideIcon } from "lucide-react";
import { useTranslations } from "next-intl";
import { Bar, BarChart, CartesianGrid, LabelList, XAxis, YAxis } from "recharts";
import { Link } from "@/i18n/navigation";
import { getStockMasterProductStats } from "@/lib/api";
import { getModuleTheme } from "@/lib/module-theme";
import type { StockMasterProductStats, StockMasterProductStatsBreakdownItem } from "@/lib/types";
import { cn } from "@/lib/utils";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { type ChartConfig, ChartContainer, ChartTooltip, ChartTooltipContent } from "@/components/ui/chart";
import { useKeyedLoad } from "@/components/module-4/use-keyed-load";
import { STOCKMASTER_BASE } from "@/components/module-4/stockmaster-common";

// The module accent (teal-600, lightened to teal-400 on the dark theme).
const MODULE_ACCENT = { light: "#0d9488", dark: "#2dd4bf" };

interface ProductStatsSectionProps {
  /** Whether the tiles may link to the Products screen. */
  canOpenProducts: boolean;
}

export function ProductStatsSection({ canOpenProducts }: ProductStatsSectionProps) {
  const t = useTranslations("stockMaster.kpi.products");
  const tKpi = useTranslations("stockMaster.kpi");
  const { badgeClassName } = getModuleTheme("module-4");

  // One fixed key: the figures don't depend on anything the user picks.
  const { data: stats, failed } = useKeyedLoad<StockMasterProductStats>("all", getStockMasterProductStats);

  return (
    <div className="flex flex-col gap-4">
      <div>
        <h2 className="text-xl font-semibold tracking-tight">{t("title")}</h2>
        <p className="text-sm text-muted-foreground">{t("description")}</p>
      </div>

      {failed && <p className="text-sm text-destructive">{tKpi("loadError")}</p>}
      {stats && (
        <>
          <div className="grid grid-cols-2 gap-4 md:grid-cols-5">
            {productTiles(stats, t).map(({ icon: Icon, label, value }) => {
              const card = (
                <Card className={cn("h-full", canOpenProducts && "transition-colors hover:bg-muted/40")}>
                  <CardContent className="flex flex-col items-center gap-2 text-center">
                    <div className={cn("flex size-10 items-center justify-center rounded-full", badgeClassName)}>
                      <Icon className="size-5" aria-hidden="true" />
                    </div>
                    <span className="text-2xl font-semibold tabular-nums">{value.toLocaleString()}</span>
                    <span className="text-xs text-muted-foreground">{label}</span>
                  </CardContent>
                </Card>
              );
              return canOpenProducts ? (
                <Link
                  key={label}
                  href={`${STOCKMASTER_BASE}/masterdata/products`}
                  className="rounded-xl focus-visible:ring-2 focus-visible:ring-ring"
                >
                  {card}
                </Link>
              ) : (
                <div key={label}>{card}</div>
              );
            })}
          </div>

          <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
            <BreakdownBarChart
              title={t("chartTypeTitle")}
              description={t("chartTypeDescription")}
              series={t("chartTypeSeries")}
              unassigned={t("unassignedLabel")}
              empty={t("chartEmpty")}
              items={stats.products_by_type}
            />
            <BreakdownBarChart
              title={t("chartCategoryTitle")}
              description={t("chartCategoryDescription")}
              series={t("chartCategorySeries")}
              unassigned={t("unassignedLabel")}
              empty={t("chartEmpty")}
              items={stats.products_by_category}
            />
            <BreakdownBarChart
              title={t("chartWarehouseTitle")}
              description={t("chartWarehouseDescription")}
              series={t("chartWarehouseSeries")}
              unassigned={t("unassignedLabel")}
              empty={t("chartEmpty")}
              items={stats.products_by_warehouse}
            />
          </div>
        </>
      )}
    </div>
  );
}

/** The five stat tiles, in display order. */
function productTiles(
  stats: StockMasterProductStats,
  t: (key: string) => string,
): { icon: LucideIcon; label: string; value: number }[] {
  return [
    { icon: Package, label: t("statTotalProducts"), value: stats.total_products },
    { icon: Ban, label: t("statBlockedProducts"), value: stats.blocked_products },
    { icon: Recycle, label: t("statConsumableProducts"), value: stats.consumable_products },
    { icon: Truck, label: t("statLogisticsProducts"), value: stats.logistics_products },
    { icon: TriangleAlert, label: t("statMissingClassification"), value: stats.products_missing_classification },
  ];
}

interface BreakdownBarChartProps {
  title: string;
  description: string;
  series: string;
  unassigned: string;
  empty: string;
  items: StockMasterProductStatsBreakdownItem[];
}

/** One horizontal bar-chart card, shared by the three breakdowns. */
function BreakdownBarChart({ title, description, series, unassigned, empty, items }: BreakdownBarChartProps) {
  const data = items.map((item) => ({ label: item.name ?? unassigned, count: item.count }));
  const config: ChartConfig = { count: { label: series, theme: MODULE_ACCENT } };
  // With no products at all there's still the zero-filled "Unassigned"
  // entry — show the empty message rather than a meaningless zero bar.
  const isEmpty = data.every((item) => item.count === 0);

  return (
    <Card>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
        <CardDescription>{description}</CardDescription>
      </CardHeader>
      <CardContent>
        {isEmpty ? (
          <p className="flex h-64 items-center justify-center text-center text-sm text-muted-foreground">{empty}</p>
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
