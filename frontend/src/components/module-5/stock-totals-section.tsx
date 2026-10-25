"use client";

// The KPI page's "Stock" section: pieces available, waiting to be washed and
// handed out over all clothing, plus how many article sizes are below their
// minimum stock (orange when any).

import { PackageCheck, Shirt, TriangleAlert, WashingMachine } from "lucide-react";
import { useTranslations } from "next-intl";
import { getAtelierStockTotals } from "@/lib/api";
import { getModuleTheme } from "@/lib/module-theme";
import type { AtelierStockTotals } from "@/lib/types";
import { cn } from "@/lib/utils";
import { Card, CardContent } from "@/components/ui/card";
import { useKeyedLoad } from "@/components/module-4/use-keyed-load";

export function StockTotalsSection() {
  const t = useTranslations("atelier.landing.stock");
  const totals = useKeyedLoad<AtelierStockTotals>("stock-totals", getAtelierStockTotals);
  // The soft pill colours of this module's accent, for the tile icons.
  const { badgeClassName } = getModuleTheme("module-5");

  const tiles = totals.data
    ? [
        { icon: PackageCheck, label: t("available"), value: totals.data.available, warn: false },
        { icon: WashingMachine, label: t("toWash"), value: totals.data.to_wash, warn: false },
        { icon: Shirt, label: t("handedOut"), value: totals.data.handed_out, warn: false },
        { icon: TriangleAlert, label: t("belowMin"), value: totals.data.below_min_stock, warn: totals.data.below_min_stock > 0 },
      ]
    : [];

  return (
    <section className="flex flex-col gap-3">
      <h2 className="text-lg font-semibold">{t("title")}</h2>
      {totals.failed && <p className="text-sm text-destructive">{t("loadFailed")}</p>}
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        {tiles.map((tile) => (
          <Card key={tile.label}>
            <CardContent className="flex items-center gap-4">
              <div
                className={cn(
                  "flex size-10 shrink-0 items-center justify-center rounded-full",
                  tile.warn ? "bg-orange-100 text-orange-700 dark:bg-orange-500/15 dark:text-orange-300" : badgeClassName,
                )}
              >
                <tile.icon className="size-5" />
              </div>
              <div>
                <p className="text-2xl font-bold">{tile.value}</p>
                <p className="text-sm text-muted-foreground">{tile.label}</p>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </section>
  );
}
