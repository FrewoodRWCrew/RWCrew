"use client";

// KarTracker's "Kar Planning" screen: a read-only report joining
// KarManagement with its status/team/transport-type lookups (see
// module_2/router.py's list_kar_planning) — step 1 of a report that will
// grow to join more tables in a later phase. Selection + per-column
// filters follow the same pattern as TagScan's TagManagement
// (components/module-1/tag-management.tsx), but there is no per-row
// edit/delete Actions column since this screen never mutates data. The
// checked rows instead feed a single "Print" toolbar button, a placeholder
// for the mass-printing feature planned for a later phase.

import { useMemo, useState } from "react";
import { useTranslations } from "next-intl";
import { toast } from "sonner";
import type { KarTrackerKarPlanningRow } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";

interface KarPlanningProps {
  initialRows: KarTrackerKarPlanningRow[];
}

/** Case-insensitive substring match, used by every free-text filter cell.
 * `null`/empty field values never match a non-empty filter. */
function textMatches(fieldValue: string | null, filterValue: string): boolean {
  if (!filterValue) return true;
  return (fieldValue ?? "").toLowerCase().includes(filterValue.toLowerCase());
}

export function KarPlanning({ initialRows }: KarPlanningProps) {
  const t = useTranslations("karTracker.karPlanning");

  const [karNummerFilter, setKarNummerFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [teamFilter, setTeamFilter] = useState("");
  const [transportTypeFilter, setTransportTypeFilter] = useState("");
  const [geolocationFilter, setGeolocationFilter] = useState("");
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set());

  const filteredRows = useMemo(() => {
    return initialRows.filter((row) => {
      if (!textMatches(row.kar_nummer, karNummerFilter)) return false;
      if (!textMatches(row.status_name, statusFilter)) return false;
      if (!textMatches(row.team_name, teamFilter)) return false;
      if (!textMatches(row.transport_type_name, transportTypeFilter)) return false;
      if (!textMatches(row.geolocation, geolocationFilter)) return false;
      return true;
    });
  }, [initialRows, karNummerFilter, statusFilter, teamFilter, transportTypeFilter, geolocationFilter]);

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

  function handlePrint() {
    toast(t("printNotImplemented"));
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight underline">{t("title")}</h1>
          <p className="text-muted-foreground">{t("description")}</p>
        </div>
        <Button onClick={handlePrint} disabled={selectedIds.size === 0}>
          {t("printButton")}
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
                <TableCell className="text-muted-foreground">{row.geolocation}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}
