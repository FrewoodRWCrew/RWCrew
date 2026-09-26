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

import { useEffect, useMemo, useState } from "react";
import { useLocale, useTranslations } from "next-intl";
import { toast } from "sonner";
import { listKarPlanning, printKarPlanning } from "@/lib/api";
import { SITE_URL } from "@/lib/config";
import { useSelectedSeason } from "@/components/shared/season-provider";
import type { KarTrackerKarPlanningReport } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";

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
    return rows.filter((row) => {
      if (!textMatches(row.kar_nummer, karNummerFilter)) return false;
      if (!textMatches(row.status_name, statusFilter)) return false;
      if (!textMatches(row.team_name, teamFilter)) return false;
      if (!textMatches(row.transport_type_name, transportTypeFilter)) return false;
      // Only the festival columns currently shown take part in filtering.
      for (const festival of festivals) {
        if (!textMatches(row.afleverlocaties[festival.id] ?? null, festivalFilters[festival.id] ?? "")) return false;
      }
      if (!textMatches(row.geolocation, geolocationFilter)) return false;
      return true;
    });
  }, [rows, festivals, karNummerFilter, statusFilter, teamFilter, transportTypeFilter, festivalFilters, geolocationFilter]);

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
                <TableHead key={festival.id} className="sticky top-0 z-20 bg-background font-bold underline">
                  {festival.name}
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
                <TableCell className="text-muted-foreground">{row.status_name}</TableCell>
                <TableCell className="text-muted-foreground">{row.team_name}</TableCell>
                <TableCell className="text-muted-foreground">{row.transport_type_name}</TableCell>
                {festivals.map((festival) => (
                  <TableCell key={festival.id} className="text-muted-foreground">
                    {row.afleverlocaties[festival.id]}
                  </TableCell>
                ))}
                <TableCell className="text-muted-foreground">{row.geolocation}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}
