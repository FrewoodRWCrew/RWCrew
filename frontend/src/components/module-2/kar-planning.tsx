"use client";

// KarTracker's "Kar Planning" screen: a read-only report joining
// KarManagement with its status/team/transport-type lookups (see
// module_2/router.py's list_kar_planning) — step 1 of a report that will
// grow to join more tables in a later phase. For the season selected in the
// header it also gets one column per active festival (between Transporttype
// and Locatie) showing the afleverlocatie planned for the kar's team there.
// Selection + per-column
// filters follow the same pattern as TagScan's TagManagement
// (components/module-1/tag-management.tsx), but there is no per-row
// edit/delete Actions column since this screen never mutates data. The
// checked rows instead feed a single "Print" toolbar button, which asks the
// backend for a PDF with one "karblad" page per checked kar (see
// module_2/karblad_pdf.py) and opens it in a new tab.
//
// To keep the wide table easy to scan: statuses are coloured pills (see
// status-colour.ts), a planned delivery location is a pill in the module's
// purple while a gap is a faint "—" (or a muted "Niet actief" when the
// kar's team unchecked that festival in Altsien Select, which counts as
// complete), each festival header counts "x/y gepland" over the visible
// rows, and the raw coordinates hide behind a
// map-pin tooltip. A line above the table counts the visible/selected karren
// and clears every filter at once.

import { useEffect, useMemo, useState } from "react";
import { MapPin } from "lucide-react";
import { useLocale, useTranslations } from "next-intl";
import { toast } from "sonner";
import { listKarPlanning, printKarPlanning } from "@/lib/api";
import { SITE_URL } from "@/lib/config";
import { getModuleTheme } from "@/lib/module-theme";
import { cn } from "@/lib/utils";
import { useSelectedSeason } from "@/components/shared/season-provider";
import { statusPillClassName } from "@/components/module-2/status-colour";
import type { KarTrackerKarPlanningReport } from "@/lib/types";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";

// The faint dash shown in a cell without a value (no team, no planned
// location, no known position), so empty cells read as "nothing" at a glance.
function EmptyValue() {
  return <span className="text-muted-foreground/40">—</span>;
}

interface KarPlanningProps {
  // The report as fetched on the server, i.e. without any festival columns
  // (the header's season is only known in the browser).
  initialReport: KarTrackerKarPlanningReport;
}

// A report fetched for one specific season, remembered together with it.
interface LoadedReport {
  seasonId: number;
  report: KarTrackerKarPlanningReport;
}

/** Case-insensitive substring match, used by every free-text filter cell.
 * `null`/empty field values never match a non-empty filter. */
function textMatches(fieldValue: string | null, filterValue: string): boolean {
  if (!filterValue) return true;
  return (fieldValue ?? "").toLowerCase().includes(filterValue.toLowerCase());
}

export function KarPlanning({ initialReport }: KarPlanningProps) {
  const t = useTranslations("karTracker.karPlanning");
  const locale = useLocale();
  const { selectedSeasonId } = useSelectedSeason();

  const [loaded, setLoaded] = useState<LoadedReport | null>(null);
  const [karNummerFilter, setKarNummerFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [teamFilter, setTeamFilter] = useState("");
  const [transportTypeFilter, setTransportTypeFilter] = useState("");
  const [geolocationFilter, setGeolocationFilter] = useState("");
  // One free-text filter per festival column, keyed by festival id.
  const [festivalFilters, setFestivalFilters] = useState<Record<number, string>>({});
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set());
  // True while the PDF is being generated, so the button can't be clicked twice.
  const [printing, setPrinting] = useState(false);

  // (Re)load the report whenever the header's season changes. The `cancelled`
  // flag drops a response that arrives after the season already changed
  // again, so a slow request can't overwrite a newer one.
  useEffect(() => {
    if (selectedSeasonId === null) return;
    let cancelled = false;

    listKarPlanning(selectedSeasonId)
      .then((report) => {
        if (!cancelled) setLoaded({ seasonId: selectedSeasonId, report });
      })
      .catch(() => {
        if (!cancelled) toast.error(t("loadError"));
      });

    return () => {
      cancelled = true;
    };
  }, [selectedSeasonId, t]);

  // No season selected -> the plain server-fetched report (no festival
  // columns). Otherwise the last report loaded for a season; while a newly
  // selected season is still loading that is the previous season's, which
  // beats flashing the columns away.
  const report = selectedSeasonId === null ? initialReport : (loaded?.report ?? initialReport);
  const rows = report.rows;
  const festivals = report.festivals;

  const filteredRows = useMemo(() => {
    // The text a festival cell shows: the planned location, "Niet actief"
    // for a festival the team unchecked, or nothing.
    const festivalCellText = (row: (typeof rows)[number], festivalId: number): string | null =>
      row.afleverlocaties[festivalId] ?? (row.inactive_festival_ids.includes(festivalId) ? t("notActive") : null);

    return rows.filter((row) => {
      if (!textMatches(row.kar_nummer, karNummerFilter)) return false;
      if (!textMatches(row.status_name, statusFilter)) return false;
      if (!textMatches(row.team_name, teamFilter)) return false;
      if (!textMatches(row.transport_type_name, transportTypeFilter)) return false;
      // Only the festival columns currently shown take part in filtering.
      // They match on the text shown in the cell, "Niet actief" included.
      for (const festival of festivals) {
        if (!textMatches(festivalCellText(row, festival.id), festivalFilters[festival.id] ?? "")) return false;
      }
      if (!textMatches(row.geolocation, geolocationFilter)) return false;
      return true;
    });
  }, [rows, festivals, karNummerFilter, statusFilter, teamFilter, transportTypeFilter, festivalFilters, geolocationFilter, t]);

  // Per festival column: how many of the visible karren are done there (the
  // "x/y gepland" line under its header): a delivery location is planned, or
  // the team doesn't take part in that festival.
  const plannedPerFestival = useMemo(() => {
    const counts: Record<number, number> = {};
    for (const festival of festivals) {
      counts[festival.id] = filteredRows.filter(
        (row) => row.afleverlocaties[festival.id] || row.inactive_festival_ids.includes(festival.id)
      ).length;
    }
    return counts;
  }, [festivals, filteredRows]);

  // True when any filter cell holds text, which enables "Filters wissen".
  const anyFilterSet =
    [karNummerFilter, statusFilter, teamFilter, transportTypeFilter, geolocationFilter].some(Boolean) ||
    Object.values(festivalFilters).some(Boolean);

  function clearFilters() {
    setKarNummerFilter("");
    setStatusFilter("");
    setTeamFilter("");
    setTransportTypeFilter("");
    setGeolocationFilter("");
    setFestivalFilters({});
  }

  // The module's own purple, used for the planned-location pills.
  const { badgeClassName: plannedPillClassName } = getModuleTheme("module-2");

  const filteredIds = useMemo(() => filteredRows.map((row) => row.id), [filteredRows]);
  const allFilteredSelected = filteredIds.length > 0 && filteredIds.every((id) => selectedIds.has(id));
  const someFilteredSelected = filteredIds.some((id) => selectedIds.has(id));

  function toggleSelectAll(checked: boolean) {
    setSelectedIds((current) => {
      const next = new Set(current);
      for (const id of filteredIds) {
        if (checked) next.add(id);
        else next.delete(id);
      }
      return next;
    });
  }

  function toggleSelectOne(rowId: number, checked: boolean) {
    setSelectedIds((current) => {
      const next = new Set(current);
      if (checked) next.add(rowId);
      else next.delete(rowId);
      return next;
    });
  }

  async function handlePrint() {
    // The festival blocks and delivery dates on a karblad belong to a season.
    if (selectedSeasonId === null) {
      toast.error(t("printNeedsSeason"));
      return;
    }

    setPrinting(true);
    try {
      // Print every checked kar, including ones a filter currently hides.
      // The QR codes point at the configured public site address, or else at
      // whatever address this page is opened on.
      const pdf = await printKarPlanning(
        selectedSeasonId,
        [...selectedIds],
        SITE_URL ?? window.location.origin,
        locale,
      );
      // Show the PDF in a new tab (the browser's viewer has the print
      // dialog); the object URL is released after the tab has had time to load it.
      const url = URL.createObjectURL(pdf);
      if (!window.open(url, "_blank")) {
        // The browser blocked the pop-up (it opened after an async call), so
        // hand the PDF over as a normal download instead.
        const link = document.createElement("a");
        link.href = url;
        link.download = "Karbladen.pdf";
        link.click();
      }
      setTimeout(() => URL.revokeObjectURL(url), 60_000);
    } catch {
      toast.error(t("printError"));
    } finally {
      setPrinting(false);
    }
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight underline">{t("title")}</h1>
          <p className="text-muted-foreground">{t("description")}</p>
        </div>
        <Button onClick={handlePrint} disabled={selectedIds.size === 0 || printing}>
          {printing ? t("printing") : t("printButton")}
        </Button>
      </div>

      {/* Count of visible/selected karren, plus one click to drop every filter. */}
      <div className="-mb-2 flex items-center justify-between gap-4 text-sm text-muted-foreground">
        <span>
          {t("rowCount", { shown: filteredRows.length, total: rows.length, selected: selectedIds.size })}
        </span>
        <Button variant="ghost" size="sm" onClick={clearFilters} disabled={!anyFilterSet}>
          {t("clearFilters")}
        </Button>
      </div>

      <TooltipProvider delay={200}>
        <div className="rounded-md border [&>div]:max-h-[65vh] [&>div]:overflow-y-auto">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="sticky top-0 z-20 bg-background">
                  <Checkbox
                    checked={allFilteredSelected}
                    indeterminate={someFilteredSelected && !allFilteredSelected}
                    onCheckedChange={(checked) => toggleSelectAll(checked === true)}
                    aria-label={t("selectAll")}
                  />
                </TableHead>
                <TableHead className="sticky top-0 z-20 bg-background font-bold underline">{t("columnKarNummer")}</TableHead>
                <TableHead className="sticky top-0 z-20 bg-background font-bold underline">{t("columnStatus")}</TableHead>
                <TableHead className="sticky top-0 z-20 bg-background font-bold underline">{t("columnTeam")}</TableHead>
                <TableHead className="sticky top-0 z-20 bg-background font-bold underline">{t("columnTransportType")}</TableHead>
                {/* One column per active festival of the selected season. */}
                {festivals.map((festival) => (
                  <TableHead key={festival.id} className="sticky top-0 z-20 bg-background">
                    <span className="font-bold underline">{festival.name}</span>
                    <span className="ml-2 text-xs font-normal text-muted-foreground">
                      {t("festivalPlanned", { planned: plannedPerFestival[festival.id] ?? 0, total: filteredRows.length })}
                    </span>
                  </TableHead>
                ))}
                <TableHead className="sticky top-0 z-20 bg-background font-bold underline">{t("columnGeolocation")}</TableHead>
              </TableRow>
              {/* The filter row: each control sits directly under the
                  column it filters. */}
              <TableRow>
                <TableHead className="sticky top-10 z-20 bg-background" />
                <TableHead className="sticky top-10 z-20 bg-background">
                  <Input
                    aria-label={t("filterKarNummer")}
                    placeholder={t("filterKarNummer")}
                    className="h-8 w-full min-w-32 font-normal"
                    value={karNummerFilter}
                    onChange={(event) => setKarNummerFilter(event.target.value)}
                  />
                </TableHead>
                <TableHead className="sticky top-10 z-20 bg-background">
                  <Input
                    aria-label={t("filterStatus")}
                    placeholder={t("filterStatus")}
                    className="h-8 w-full min-w-32 font-normal"
                    value={statusFilter}
                    onChange={(event) => setStatusFilter(event.target.value)}
                  />
                </TableHead>
                <TableHead className="sticky top-10 z-20 bg-background">
                  <Input
                    aria-label={t("filterTeam")}
                    placeholder={t("filterTeam")}
                    className="h-8 w-full min-w-32 font-normal"
                    value={teamFilter}
                    onChange={(event) => setTeamFilter(event.target.value)}
                  />
                </TableHead>
                <TableHead className="sticky top-10 z-20 bg-background">
                  <Input
                    aria-label={t("filterTransportType")}
                    placeholder={t("filterTransportType")}
                    className="h-8 w-full min-w-32 font-normal"
                    value={transportTypeFilter}
                    onChange={(event) => setTransportTypeFilter(event.target.value)}
                  />
                </TableHead>
                {festivals.map((festival) => (
                  <TableHead key={festival.id} className="sticky top-10 z-20 bg-background">
                    <Input
                      aria-label={t("filterFestival", { festival: festival.name })}
                      placeholder={t("filterFestival", { festival: festival.name })}
                      className="h-8 w-full min-w-32 font-normal"
                      value={festivalFilters[festival.id] ?? ""}
                      onChange={(event) =>
                        setFestivalFilters((current) => ({ ...current, [festival.id]: event.target.value }))
                      }
                    />
                  </TableHead>
                ))}
                <TableHead className="sticky top-10 z-20 bg-background">
                  <Input
                    aria-label={t("filterGeolocation")}
                    placeholder={t("filterGeolocation")}
                    className="h-8 w-full min-w-32 font-normal"
                    value={geolocationFilter}
                    onChange={(event) => setGeolocationFilter(event.target.value)}
                  />
                </TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filteredRows.map((row) => (
                <TableRow key={row.id} className="group">
                  <TableCell>
                    <Checkbox
                      checked={selectedIds.has(row.id)}
                      onCheckedChange={(checked) => toggleSelectOne(row.id, checked === true)}
                      aria-label={t("selectRow", { karNummer: row.kar_nummer })}
                    />
                  </TableCell>
                  <TableCell className="font-medium">{row.kar_nummer}</TableCell>
                  <TableCell>
                    <Badge className={statusPillClassName(row.status_name)}>{row.status_name}</Badge>
                  </TableCell>
                  <TableCell>{row.team_name ?? <EmptyValue />}</TableCell>
                  <TableCell>
                    <Badge variant="outline">{row.transport_type_name}</Badge>
                  </TableCell>
                  {festivals.map((festival) => (
                    <TableCell key={festival.id}>
                      {row.afleverlocaties[festival.id] ? (
                        <Badge className={cn("font-normal", plannedPillClassName)}>
                          {row.afleverlocaties[festival.id]}
                        </Badge>
                      ) : row.inactive_festival_ids.includes(festival.id) ? (
                        // The team unchecked this festival in Altsien Select: nothing to plan.
                        <span className="text-muted-foreground italic">{t("notActive")}</span>
                      ) : (
                        <EmptyValue />
                      )}
                    </TableCell>
                  ))}
                  <TableCell>
                    {row.geolocation ? (
                      // The coordinates only matter now and then: a pin, with them in a tooltip.
                      <Tooltip>
                        <TooltipTrigger
                          render={
                            <span
                              tabIndex={0}
                              aria-label={row.geolocation}
                              className="inline-flex cursor-help text-muted-foreground hover:text-foreground"
                            />
                          }
                        >
                          <MapPin className="size-4" />
                        </TooltipTrigger>
                        <TooltipContent>{row.geolocation}</TooltipContent>
                      </Tooltip>
                    ) : (
                      <span aria-label={t("noLocation")}>
                        <EmptyValue />
                      </span>
                    )}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      </TooltipProvider>
    </div>
  );
}
