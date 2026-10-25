"use client";

// The KPI page's "Reservaties" section: per festival of the chosen season
// the persons and pieces per day, how many teams reserved, how many of those
// still have no package, and how many teams were probably forgotten there
// (reserved at another festival of the season, but nothing here). Clicking
// that count shows the team names with a link to the festival's Reservaties.
// Has the module's own season dropdown (?season=).

import { Fragment, useState } from "react";
import { ChevronDown, ChevronRight } from "lucide-react";
import { useTranslations } from "next-intl";
import { Link } from "@/i18n/navigation";
import { getAtelierReservationStats } from "@/lib/api";
import { formatDateNl } from "@/lib/date-time";
import type { AtelierFestivalReservationStats, Season } from "@/lib/types";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { AtelierSeasonSelect, useAtelierSeasonId } from "@/components/module-5/atelier-season-select";
import { useKeyedLoad } from "@/components/module-4/use-keyed-load";

interface ReservationStatsSectionProps {
  seasons: Season[];
}

export function ReservationStatsSection({ seasons }: ReservationStatsSectionProps) {
  const t = useTranslations("atelier.landing.reservations");
  const seasonId = useAtelierSeasonId(seasons);
  const stats = useKeyedLoad<AtelierFestivalReservationStats[]>(seasonId === null ? null : String(seasonId), () =>
    getAtelierReservationStats(seasonId!),
  );
  // The festival whose forgotten teams are shown under its row.
  const [openFestivalId, setOpenFestivalId] = useState<number | null>(null);

  return (
    <section className="flex flex-col gap-3">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <h2 className="text-lg font-semibold">{t("title")}</h2>
        <AtelierSeasonSelect seasons={seasons} seasonId={seasonId} />
      </div>
      {stats.failed && <p className="text-sm text-destructive">{t("loadFailed")}</p>}
      <div className="rounded-md border [&>div]:max-h-[45vh] [&>div]:overflow-y-auto">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="sticky top-0 z-20 bg-background font-bold underline">{t("columnFestival")}</TableHead>
              <TableHead className="sticky top-0 z-20 bg-background font-bold underline">{t("columnDays")}</TableHead>
              <TableHead className="sticky top-0 z-20 bg-background text-right font-bold underline">
                {t("columnPersons")}
              </TableHead>
              <TableHead className="sticky top-0 z-20 bg-background text-right font-bold underline">
                {t("columnPieces")}
              </TableHead>
              <TableHead className="sticky top-0 z-20 bg-background text-right font-bold underline">
                {t("columnTeams")}
              </TableHead>
              <TableHead className="sticky top-0 z-20 bg-background text-right font-bold underline">
                {t("columnWithoutPackage")}
              </TableHead>
              <TableHead
                className="sticky top-0 z-20 bg-background text-right font-bold underline"
                title={t("columnMissingHelp")}
              >
                {t("columnMissing")}
              </TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {(stats.data ?? []).length === 0 && (
              <TableRow>
                <TableCell colSpan={7} className="text-center text-muted-foreground">
                  {stats.isLoading ? t("loading") : t("empty")}
                </TableCell>
              </TableRow>
            )}
            {(stats.data ?? []).map((row) => {
              const isOpen = openFestivalId === row.festival.id;
              const missingCount = row.teams_missing.length;
              return (
                <Fragment key={row.festival.id}>
                  <TableRow>
                    <TableCell className="font-medium">{row.festival.name}</TableCell>
                    <TableCell className="text-muted-foreground">
                      {formatDateNl(row.festival.start_date)} · {t("days", { count: row.festival.days.length })}
                    </TableCell>
                    <TableCell className="text-right">{row.persons_per_day}</TableCell>
                    <TableCell className="text-right">{row.pieces_per_day}</TableCell>
                    <TableCell className="text-right">{row.teams_reserved}</TableCell>
                    <TableCell
                      className={row.teams_without_package > 0 ? "text-right font-medium text-destructive" : "text-right"}
                    >
                      {row.teams_without_package}
                    </TableCell>
                    <TableCell className="text-right">
                      {missingCount > 0 ? (
                        // The count opens the list of forgotten teams under this row.
                        <button
                          type="button"
                          onClick={() => setOpenFestivalId(isOpen ? null : row.festival.id)}
                          aria-expanded={isOpen}
                          className="inline-flex items-center gap-1 font-medium text-orange-600 hover:underline dark:text-orange-400"
                        >
                          {isOpen ? <ChevronDown className="size-4" /> : <ChevronRight className="size-4" />}
                          {missingCount}
                        </button>
                      ) : (
                        0
                      )}
                    </TableCell>
                  </TableRow>
                  {isOpen && (
                    <TableRow className="bg-orange-50 hover:bg-orange-50 dark:bg-orange-500/10">
                      <TableCell colSpan={7} className="whitespace-normal">
                        <p className="text-sm">
                          {t("missingIntro")} <span className="font-medium">{row.teams_missing.join(", ")}</span>
                        </p>
                        <div className="mt-1 flex flex-wrap items-center gap-3 text-sm">
                          <Link
                            href={`/modules/module-5/reservations?season=${seasonId}&festival=${row.festival.id}`}
                            className="font-medium text-primary hover:underline"
                          >
                            {t("missingLink")}
                          </Link>
                          <span className="text-muted-foreground">{t("missingSilence")}</span>
                        </div>
                      </TableCell>
                    </TableRow>
                  )}
                </Fragment>
              );
            })}
          </TableBody>
        </Table>
      </div>
    </section>
  );
}
