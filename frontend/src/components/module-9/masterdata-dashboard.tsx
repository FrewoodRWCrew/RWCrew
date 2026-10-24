"use client";

// MasterData's landing dashboard ("Masterdata Overview"): stat tiles styled
// after TagScan's own dashboard (components/module-1/tag-dashboard.tsx).
// The product tiles and the Type/Category/Warehouse charts moved to
// StockMaster's KPI page together with the product screens (see
// components/module-4/product-stats-section.tsx), so only the seasons
// count is left here.

import { CalendarDays, type LucideIcon } from "lucide-react";
import { useTranslations } from "next-intl";
import { Card, CardContent } from "@/components/ui/card";
import { getModuleTheme } from "@/lib/module-theme";
import { cn } from "@/lib/utils";
import type { MasterDataDashboardStats } from "@/lib/types";

interface MasterDataDashboardProps {
  stats: MasterDataDashboardStats;
}

export function MasterDataDashboard({ stats }: MasterDataDashboardProps) {
  const t = useTranslations("masterdata.landing");
  const { badgeClassName } = getModuleTheme("module-9");

  const statTiles: { icon: LucideIcon; label: string; value: number }[] = [
    { icon: CalendarDays, label: t("statTotalSeasons"), value: stats.total_seasons },
  ];

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
    </div>
  );
}
