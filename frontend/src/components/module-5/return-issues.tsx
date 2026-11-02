"use client";

// Atelier's "Balie > Retourproblemen" screen: the pieces that came back with a
// return status (damaged, very dirty, ...), newest first. Read-only. Filters:
// festival + day at the top (they decide what's loaded; "Alle festivals" loads
// the whole season, without a day choice) and a text filter above every column
// (client-side), so the Festival column narrows the season down to one
// festival. The Excel button downloads the pieces shown. No email column, for
// privacy (GDPR).

import { useState } from "react";
import { Download } from "lucide-react";
import { useLocale, useTranslations } from "next-intl";
import { toast } from "sonner";
import { exportAtelierReturnIssues, listAtelierReturnIssues } from "@/lib/api";
import { formatDateNl, formatDateTimeNl } from "@/lib/date-time";
import type { AtelierReturnIssue, Season } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { SearchableSelect } from "@/components/ui/searchable-select";
import { Table, TableBody, TableCell, TableFooter, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { AtelierFestivalSelect, useAtelierFestival } from "@/components/module-5/atelier-festival-select";
import { AtelierSeasonSelect, useAtelierSeasonId } from "@/components/module-5/atelier-season-select";
import { FilterHeadCell, useColumnFilters } from "@/components/module-5/column-filters";
import { saveExcel } from "@/components/module-5/desk-common";
import { useKeyedLoad } from "@/components/module-4/use-keyed-load";

// The day filter's "every day" choice (Base UI's Select needs a non-empty value).
const ALL = "all";

// The table's columns, in order (each has a text filter above it).
const COLUMNS = ["status", "article", "size", "festival", "team", "person", "bracelet", "day", "returned", "by"] as const;
type Column = (typeof COLUMNS)[number];

interface ReturnIssuesProps {
  seasons: Season[];
}

export function ReturnIssues({ seasons }: ReturnIssuesProps) {
  const t = useTranslations("atelier.returnIssues");
  const tFit = useTranslations("atelier.fits");
  const locale = useLocale();
  const seasonId = useAtelierSeasonId(seasons);
  const { festivals, festival, allFestivals } = useAtelierFestival(seasonId, { allowAll: true });
  const [day, setDay] = useState<string>(ALL);
  // The chosen day (null = every day); "Alle festivals" has no day choice.
  const dayFilter = allFestivals || day === ALL ? null : day;
  const [isDownloading, setIsDownloading] = useState(false);
  const { filters, setFilter, matches, active } = useColumnFilters<Column>();

  // What's loaded: the whole season, or one festival (and day).
  const key = allFestivals && seasonId !== null ? `all-${seasonId}` : festival ? `${festival.id}-${dayFilter}` : null;
  const rows = useKeyedLoad<AtelierReturnIssue[]>(key, () =>
    allFestivals
      ? listAtelierReturnIssues({ festivalId: null, seasonId, day: null })
      : listAtelierReturnIssues({ festivalId: festival!.id, day: dayFilter }),
  );
  const issues = rows.data ?? [];

  // The texts a row shows per column (and filters on).
  function cells(issue: AtelierReturnIssue): Record<Column, string | null> {
    return {
      status: issue.status_name,
      article: issue.article_name,
      size: `${issue.size_name} · ${tFit(issue.fit)}`,
      festival: issue.festival_name,
      team: issue.team_name,
      person: issue.person_name,
      bracelet: issue.bracelet_number,
      day: formatDateNl(issue.day),
      returned: formatDateTimeNl(issue.returned_at),
      by: issue.returned_by_name,
    };
  }
  const shown = issues.filter((issue) => matches(cells(issue)));

  // The Excel file of the pieces shown (column filters included).
  async function handleDownload() {
    const seasonName = seasons.find((season) => season.id === seasonId)?.name;
    const fileName = allFestivals ? seasonName : festival?.name;
    if (!fileName) return;
    setIsDownloading(true);
    try {
      const blob = await exportAtelierReturnIssues({
        festivalId: allFestivals ? null : festival!.id,
        seasonId: allFestivals ? seasonId : null,
        day: dayFilter,
        lineIds: shown.map((issue) => issue.line_id),
        locale,
      });
      saveExcel(blob, "atelier-retourproblemen", fileName);
    } catch {
      toast.error(t("downloadFailed"));
    } finally {
      setIsDownloading(false);
    }
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight underline">{t("title")}</h1>
          <p className="text-muted-foreground">{t("description")}</p>
        </div>
        <div className="flex flex-wrap items-end gap-3">
          <AtelierFestivalSelect festivals={festivals} festival={festival} allowAll allFestivals={allFestivals} />
          {/* The day choice only for one festival (days differ per festival). */}
          {!allFestivals && (
            <div className="flex w-40 flex-col gap-2">
              <Label htmlFor="atelier-return-issues-day">{t("dayLabel")}</Label>
              <SearchableSelect
                value={day}
                onValueChange={(value) => setDay(value ?? ALL)}
                id="atelier-return-issues-day"
                className="w-full"
                renderValue={(value: string | null) => (value && value !== ALL ? formatDateNl(value) : t("allDays"))}
                options={[
                  { value: ALL, label: t("allDays") },
                  ...(festival?.days ?? []).map((item) => ({ value: item, label: formatDateNl(item) })),
                ]}
              />
            </div>
          )}
          <AtelierSeasonSelect seasons={seasons} seasonId={seasonId} />
          <Button variant="outline" disabled={shown.length === 0 || isDownloading} onClick={() => void handleDownload()}>
            <Download className="size-4" />
            {t("download")}
          </Button>
        </div>
      </div>

      <div className="rounded-md border [&>div]:max-h-[65vh] [&>div]:overflow-y-auto">
        <Table>
          <TableHeader>
            <TableRow>
              {COLUMNS.map((column) => (
                <TableHead key={column} className="sticky top-0 z-20 bg-background font-bold underline">
                  {t(column)}
                </TableHead>
              ))}
            </TableRow>
            {/* One text filter above every column. */}
            <TableRow>
              {COLUMNS.map((column) => (
                <FilterHeadCell
                  key={column}
                  label={t("filter", { column: t(column) })}
                  value={filters[column]}
                  onChange={(value) => setFilter(column, value)}
                />
              ))}
            </TableRow>
          </TableHeader>
          <TableBody>
            {shown.length === 0 && (
              <TableRow>
                <TableCell colSpan={COLUMNS.length} className="text-center text-muted-foreground">
                  {rows.isLoading ? t("loading") : issues.length > 0 ? t("noMatch") : t("empty")}
                </TableCell>
              </TableRow>
            )}
            {shown.map((issue) => {
              const row = cells(issue);
              return (
                <TableRow key={issue.line_id}>
                  <TableCell className="font-medium">{row.status}</TableCell>
                  <TableCell>{row.article}</TableCell>
                  <TableCell>{row.size}</TableCell>
                  <TableCell>{row.festival}</TableCell>
                  <TableCell>{row.team}</TableCell>
                  <TableCell>{row.person}</TableCell>
                  <TableCell className="font-mono text-xs">{row.bracelet}</TableCell>
                  <TableCell>{row.day}</TableCell>
                  <TableCell className="text-sm text-muted-foreground">{row.returned}</TableCell>
                  <TableCell className="text-sm text-muted-foreground">{row.by}</TableCell>
                </TableRow>
              );
            })}
          </TableBody>
          {shown.length > 0 && (
            <TableFooter>
              <TableRow>
                <TableCell colSpan={COLUMNS.length} className="font-bold">
                  {t("total", { pieces: shown.length })}
                  {active && (
                    <span className="ml-3 font-normal text-muted-foreground">
                      {t("filteredOf", { shown: shown.length, total: issues.length })}
                    </span>
                  )}
                </TableCell>
              </TableRow>
            </TableFooter>
          )}
        </Table>
      </div>
    </div>
  );
}
