"use client";

// The KPI page's "Gewassen" section: how many pieces were washed in the
// season chosen above (the Reservaties section's dropdown, ?season=), as a
// total tile and a table per festival (subtotal) with one row per day. A wash
// is linked to a festival by its date; days after a festival land in the
// "no festival" group of that season (see backend module_5/wash_stats.py).

import { Fragment } from "react";
import { WashingMachine } from "lucide-react";
import { useTranslations } from "next-intl";
import { getAtelierWashStats } from "@/lib/api";
import { formatDateNl } from "@/lib/date-time";
import { getModuleTheme } from "@/lib/module-theme";
import type { AtelierWashStats, Season } from "@/lib/types";
import { cn } from "@/lib/utils";
import { Card, CardContent } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { useAtelierSeasonId } from "@/components/module-5/atelier-season-select";
import { useKeyedLoad } from "@/components/module-4/use-keyed-load";

interface WashStatsSectionProps {
  seasons: Season[];
}

export function WashStatsSection({ seasons }: WashStatsSectionProps) {
  const t = useTranslations("atelier.landing.wash");
  const seasonId = useAtelierSeasonId(seasons);
  const stats = useKeyedLoad<AtelierWashStats>(seasonId === null ? null : String(seasonId), () =>
    getAtelierWashStats(seasonId!),
  );
  // The soft pill colours of this module's accent, for the tile icon.
  const { badgeClassName } = getModuleTheme("module-5");
  const seasonName = seasons.find((season) => season.id === seasonId)?.name ?? "";
  const festivals = stats.data?.festivals ?? [];

  return (
    <section className="flex flex-col gap-3">
      <h2 className="text-lg font-semibold">{t("title", { season: seasonName })}</h2>
      {stats.failed && <p className="text-sm text-destructive">{t("loadFailed")}</p>}

      {/* The season total. */}
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <Card>
          <CardContent className="flex items-center gap-4">
            <div className={cn("flex size-10 shrink-0 items-center justify-center rounded-full", badgeClassName)}>
              <WashingMachine className="size-5" />
            </div>
            <div>
              <p className="text-2xl font-bold">{stats.data?.total ?? 0}</p>
              <p className="text-sm text-muted-foreground">{t("total")}</p>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Per festival its subtotal, then one row per washed day. */}
      <div className="max-w-xl rounded-md border [&>div]:max-h-[45vh] [&>div]:overflow-y-auto">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="sticky top-0 z-20 bg-background font-bold underline">{t("columnDay")}</TableHead>
              <TableHead className="sticky top-0 z-20 bg-background text-right font-bold underline">
                {t("columnPieces")}
              </TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {festivals.length === 0 && (
              <TableRow>
                <TableCell colSpan={2} className="text-center text-muted-foreground">
                  {stats.isLoading ? t("loading") : t("empty")}
                </TableCell>
              </TableRow>
            )}
            {festivals.map((festival) => (
              <Fragment key={festival.festival_id ?? "none"}>
                <TableRow className="bg-muted/60 hover:bg-muted/60">
                  <TableCell className="font-bold">{festival.festival_name ?? t("noFestival")}</TableCell>
                  <TableCell className="text-right font-bold">{festival.pieces}</TableCell>
                </TableRow>
                {festival.days.map((day) => (
                  <TableRow key={day.day}>
                    <TableCell className="pl-6">{formatDateNl(day.day)}</TableCell>
                    <TableCell className="text-right">{day.pieces}</TableCell>
                  </TableRow>
                ))}
              </Fragment>
            ))}
          </TableBody>
        </Table>
      </div>
    </section>
  );
}
