"use client";

// The KPI page's "Masterdata" section: stat tiles for the clothing catalogue
// (active articles, sizes and article sizes). What each team gets is part of
// its reservation, so those figures are in the Reservaties section below.

import { Ruler, Shirt, Tags } from "lucide-react";
import { useTranslations } from "next-intl";
import { getAtelierMasterdataStats } from "@/lib/api";
import { getModuleTheme } from "@/lib/module-theme";
import type { AtelierMasterdataStats } from "@/lib/types";
import { cn } from "@/lib/utils";
import { Card, CardContent } from "@/components/ui/card";
import { useKeyedLoad } from "@/components/module-4/use-keyed-load";

export function MasterdataStatsSection() {
  const t = useTranslations("atelier.landing.masterdata");
  const stats = useKeyedLoad<AtelierMasterdataStats>("masterdata", getAtelierMasterdataStats);
  // The soft pill colours of this module's accent, for the tile icons.
  const { badgeClassName } = getModuleTheme("module-5");

  const tiles = stats.data
    ? [
        {
          icon: Shirt,
          label: t("articles"),
          value: stats.data.articles_active,
          hint: stats.data.articles_inactive > 0 ? t("articlesInactive", { count: stats.data.articles_inactive }) : null,
        },
        { icon: Ruler, label: t("sizes"), value: stats.data.sizes_active, hint: null },
        { icon: Tags, label: t("articleSizes"), value: stats.data.article_sizes_active, hint: null },
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
                {tile.hint && <p className="text-xs text-muted-foreground">{tile.hint}</p>}
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </section>
  );
}
