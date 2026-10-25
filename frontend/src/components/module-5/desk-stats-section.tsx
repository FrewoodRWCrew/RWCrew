"use client";

// The KPI page's "Balie" section: pieces handed out today, pieces not
// returned yet (over all days) and the people who still have something.

import { PackageMinus, PackagePlus, Users } from "lucide-react";
import { useTranslations } from "next-intl";
import { getAtelierDeskStats } from "@/lib/api";
import { getModuleTheme } from "@/lib/module-theme";
import type { AtelierDeskStats } from "@/lib/types";
import { cn } from "@/lib/utils";
import { Card, CardContent } from "@/components/ui/card";
import { useKeyedLoad } from "@/components/module-4/use-keyed-load";

export function DeskStatsSection() {
  const t = useTranslations("atelier.landing.desk");
  const stats = useKeyedLoad<AtelierDeskStats>("desk-stats", getAtelierDeskStats);
  // The soft pill colours of this module's accent, for the tile icons.
  const { badgeClassName } = getModuleTheme("module-5");

  const tiles = stats.data
    ? [
        { icon: PackagePlus, label: t("handedOutToday"), value: stats.data.handed_out_today },
        { icon: PackageMinus, label: t("stillOut"), value: stats.data.still_out },
        { icon: Users, label: t("personsWithOpen"), value: stats.data.persons_with_open },
      ]
    : [];

  return (
    <section className="flex flex-col gap-3">
      <h2 className="text-lg font-semibold">{t("title")}</h2>
      {stats.failed && <p className="text-sm text-destructive">{t("loadFailed")}</p>}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        {tiles.map((tile) => (
          <Card key={tile.label}>
            <CardContent className="flex items-center gap-4">
              <div className={cn("flex size-10 shrink-0 items-center justify-center rounded-full", badgeClassName)}>
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
