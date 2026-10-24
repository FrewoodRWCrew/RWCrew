"use client";

// KarTracker's "Initiële leverplanning" screen (Planningsanalyses group): for
// the season selected in the header, which karren have to be delivered where
// at the start — see module_2/initial_delivery_service.py for the rule (the
// location planned for the kar's team at its first festival).
//
// Above the table: the overall total and the totals per distributiepunt.
// The table is grouped first per distributiepunt (a purple header row, in the
// order of its first location in the tour), then per delivery location (a
// grey header row, in the order of the delivery tour "Leveringsvolgorde";
// locations without a position last), followed by the karren delivered there.
//
// Every kar line has a checkbox; Shift-click ticks (or unticks) the whole
// range since the previous click, and the checkbox on a distributiepunt or
// location row does all its karren at once. "Print leverplanning" turns the
// ticked karren into a landscape PDF for the drivers (pick up at the
// distributiepunt, deliver at the afleverlocatie — module_2/delivery_planning_pdf.py),
// optionally with a page showing the delivery route on the ground plan.
//
// A filter row under the column headings narrows the karren shown: a dropdown
// for Status, free text for the other columns (the Positie filter matches the
// location's position, name, description and zone). Locations and
// distributiepunten without a matching kar disappear and their counts follow
// the filter; "select all", the group checkboxes and Shift ranges only touch
// the karren shown. Ticked karren stay ticked (and printed) when a filter hides them.

import { Fragment, useEffect, useMemo, useRef, useState, type MouseEvent } from "react";
import { useLocale, useTranslations } from "next-intl";
import { toast } from "sonner";
import { getInitialDelivery, printInitialDelivery } from "@/lib/api";
import { formatDateNl } from "@/lib/date-time";
import { getModuleTheme } from "@/lib/module-theme";
import { useSelectedSeason } from "@/components/shared/season-provider";
import { statusPillClassName } from "@/components/module-2/status-colour";
import type { KarTrackerInitialDelivery } from "@/lib/types";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";

// The number of columns (checkbox included), so a header row can span all of them.
const COLUMN_COUNT = 8;

// A planning fetched for one specific season, remembered together with it.
interface LoadedPlanning {
  seasonId: number;
  planning: KarTrackerInitialDelivery;
}

// The ticked karren, remembered with the season they belong to so another
// season starts with nothing ticked.
interface Selection {
  seasonId: number | null;
  ids: Set<number>;
}

// The free-text column filters (Status has its own dropdown).
interface TextFilters {
  location: string;
  karNummer: string;
  team: string;
  transportType: string;
  festival: string;
  deliveryDate: string;
}

const EMPTY_TEXT_FILTERS: TextFilters = {
  location: "",
  karNummer: "",
  team: "",
  transportType: "",
  festival: "",
  deliveryDate: "",
};

// The Status dropdown's "no filter" value.
const ALL_STATUSES = "__all__";

/** Case-insensitive substring match; an empty filter matches everything. */
function textMatches(fieldValue: string | null, filterValue: string): boolean {
  if (!filterValue) return true;
  return (fieldValue ?? "").toLowerCase().includes(filterValue.trim().toLowerCase());
}

// What a group checkbox shows for its karren: all, some or none ticked.
function groupState(karIds: number[], selected: Set<number>): { checked: boolean; indeterminate: boolean } {
  const count = karIds.filter((id) => selected.has(id)).length;
  return { checked: count > 0 && count === karIds.length, indeterminate: count > 0 && count < karIds.length };
}

export function InitialDeliveryScreen() {
  const t = useTranslations("karTracker.initialDelivery");
  const locale = useLocale();
  const { selectedSeasonId } = useSelectedSeason();
  const { badgeClassName } = getModuleTheme("module-2");

  const [loaded, setLoaded] = useState<LoadedPlanning | null>(null);
  const [selection, setSelection] = useState<Selection>({ seasonId: null, ids: new Set() });
  const [includeMap, setIncludeMap] = useState(false);
  const [textFilters, setTextFilters] = useState<TextFilters>(EMPTY_TEXT_FILTERS);
  const [statusFilter, setStatusFilter] = useState(ALL_STATUSES);
  // True while the PDF is being generated, so the button can't be clicked twice.
  const [printing, setPrinting] = useState(false);
  // The kar clicked last (start of a Shift range) and whether the click that
  // is being handled had Shift held (Base UI's change event has no modifier keys).
  const anchorRef = useRef<number | null>(null);
  const shiftRef = useRef(false);

  // (Re)load whenever the header's season changes. The `cancelled` flag drops
  // a response that arrives after the season already changed again.
  useEffect(() => {
    if (selectedSeasonId === null) return;
    let cancelled = false;

    getInitialDelivery(selectedSeasonId)
      .then((planning) => {
        if (!cancelled) setLoaded({ seasonId: selectedSeasonId, planning });
      })
      .catch(() => {
        if (!cancelled) toast.error(t("loadError"));
      });

    return () => {
      cancelled = true;
    };
  }, [selectedSeasonId, t]);

  // While a newly selected season loads, the previous one stays on screen.
  const planning = loaded?.planning ?? null;
  // Ticks only count for the season they were made in.
  const selectedIds = useMemo(
    () => (selection.seasonId === selectedSeasonId ? selection.ids : new Set<number>()),
    [selection, selectedSeasonId],
  );

  // The statuses in this planning, for the Status dropdown.
  const statusOptions = useMemo(
    () =>
      [
        ...new Set(
          planning?.distributiepunten.flatMap((distributiepunt) =>
            distributiepunt.locations.flatMap((location) => location.karren.map((kar) => kar.status_name)),
          ) ?? [],
        ),
      ].sort((a, b) => a.localeCompare(b)),
    [planning],
  );

  const anyFilterSet = statusFilter !== ALL_STATUSES || Object.values(textFilters).some((value) => value !== "");

  // The planning with only the karren matching every filter; locations and
  // distributiepunten left empty drop out and the counts follow.
  const filteredGroups = useMemo(() => {
    if (planning === null) return [];
    return planning.distributiepunten.flatMap((distributiepunt) => {
      const locations = distributiepunt.locations.flatMap((location) => {
        const locationText = [location.terrein_positie, location.name, location.description, location.zone_name]
          .filter((part) => part !== null)
          .join(" ");
        if (!textMatches(locationText, textFilters.location)) return [];
        const karren = location.karren.filter(
          (kar) =>
            (statusFilter === ALL_STATUSES || kar.status_name === statusFilter) &&
            textMatches(kar.kar_nummer, textFilters.karNummer) &&
            textMatches(kar.team_name, textFilters.team) &&
            textMatches(kar.transport_type_name, textFilters.transportType) &&
            textMatches(kar.festival_name, textFilters.festival) &&
            textMatches(formatDateNl(kar.delivery_date), textFilters.deliveryDate),
        );
        return karren.length > 0 ? [{ ...location, karren }] : [];
      });
      const count = locations.reduce((sum, location) => sum + location.karren.length, 0);
      return locations.length > 0 ? [{ ...distributiepunt, locations, count }] : [];
    });
  }, [planning, textFilters, statusFilter]);

  // Every kar id shown, in screen order (the order a Shift range runs in).
  const allKarIds = useMemo(
    () =>
      filteredGroups.flatMap((distributiepunt) =>
        distributiepunt.locations.flatMap((location) => location.karren.map((kar) => kar.id)),
      ),
    [filteredGroups],
  );

  /** Sets one text filter. */
  function setTextFilter(key: keyof TextFilters, value: string) {
    setTextFilters((current) => ({ ...current, [key]: value }));
  }

  /** Drops every filter at once. */
  function clearFilters() {
    setTextFilters(EMPTY_TEXT_FILTERS);
    setStatusFilter(ALL_STATUSES);
  }

  /** Tick or untick these karren, keeping the rest of the selection. */
  function setMany(karIds: number[], checked: boolean) {
    const next = new Set(selectedIds);
    for (const id of karIds) {
      if (checked) next.add(id);
      else next.delete(id);
    }
    setSelection({ seasonId: selectedSeasonId, ids: next });
  }

  /** One kar's checkbox: with Shift, the whole range since the last click. */
  function toggleKar(karId: number, checked: boolean) {
    const anchor = anchorRef.current;
    const from = anchor === null ? -1 : allKarIds.indexOf(anchor);
    const to = allKarIds.indexOf(karId);
    if (shiftRef.current && from !== -1 && to !== -1) {
      setMany(allKarIds.slice(Math.min(from, to), Math.max(from, to) + 1), checked);
    } else {
      setMany([karId], checked);
    }
    shiftRef.current = false;
    anchorRef.current = karId;
  }

  /** Remembers whether Shift was held for the checkbox click inside this cell. */
  function rememberShift(event: MouseEvent) {
    shiftRef.current = event.shiftKey;
  }

  async function handlePrint() {
    if (selectedSeasonId === null || selectedIds.size === 0) return;

    setPrinting(true);
    try {
      const pdf = await printInitialDelivery(selectedSeasonId, [...selectedIds], includeMap, locale);
      // Show the PDF in a new tab (the browser's viewer has the print
      // dialog); the object URL is released after the tab has had time to load it.
      const url = URL.createObjectURL(pdf);
      if (!window.open(url, "_blank")) {
        // The browser blocked the pop-up (it opened after an async call), so
        // hand the PDF over as a normal download instead.
        const link = document.createElement("a");
        link.href = url;
        link.download = "Leverplanning.pdf";
        link.click();
      }
      setTimeout(() => URL.revokeObjectURL(url), 60_000);
    } catch {
      toast.error(t("printError"));
    } finally {
      setPrinting(false);
    }
  }

  const allState = groupState(allKarIds, selectedIds);

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight underline">{t("title")}</h1>
          <p className="text-muted-foreground">{t("description")}</p>
        </div>
        {/* Print the ticked karren, optionally with the route map page. */}
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <Checkbox
              id="initial-delivery-include-map"
              checked={includeMap}
              onCheckedChange={(checked) => setIncludeMap(checked === true)}
            />
            <Label htmlFor="initial-delivery-include-map">{t("includeMap")}</Label>
          </div>
          <Button onClick={handlePrint} disabled={selectedIds.size === 0 || printing}>
            {printing ? t("printing") : t("printButton")}
          </Button>
        </div>
      </div>

      {selectedSeasonId === null ? (
        <p className="text-sm text-muted-foreground">{t("noSeason")}</p>
      ) : planning === null ? (
        <p className="text-sm text-muted-foreground">{t("loading")}</p>
      ) : planning.distributiepunten.length === 0 ? (
        <p className="text-sm text-muted-foreground">{t("empty")}</p>
      ) : (
        <>
          {/* The totals: overall, then one pill per distributiepunt; the selection count on the right. */}
          <div className="flex flex-wrap items-center gap-2 text-sm">
            <span className="font-semibold">{t("total", { count: planning.total })}</span>
            <span className="ml-2 text-muted-foreground">{t("perDistributiepunt")}:</span>
            {planning.distributiepunten.map((distributiepunt) => (
              <Badge key={distributiepunt.id} className={badgeClassName}>
                {distributiepunt.name}: {distributiepunt.count}
              </Badge>
            ))}
            <span className="ml-auto text-muted-foreground">
              {t("shownCount", { shown: allKarIds.length, total: planning.total })} ·{" "}
              {t("selectedCount", { selected: selectedIds.size })}
              <span className="ml-2 text-xs">· {t("shiftHint")}</span>
            </span>
            <Button variant="ghost" size="sm" onClick={clearFilters} disabled={!anyFilterSet}>
              {t("clearFilters")}
            </Button>
          </div>

          <div className="rounded-md border [&>div]:max-h-[65vh] [&>div]:overflow-y-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="sticky top-0 z-20 w-10 bg-background">
                    <Checkbox
                      checked={allState.checked}
                      indeterminate={allState.indeterminate}
                      onCheckedChange={(checked) => setMany(allKarIds, checked === true)}
                      aria-label={t("selectAll")}
                    />
                  </TableHead>
                  <TableHead className="sticky top-0 z-20 bg-background font-bold underline">{t("columnPosition")}</TableHead>
                  <TableHead className="sticky top-0 z-20 bg-background font-bold underline">{t("columnKarNummer")}</TableHead>
                  <TableHead className="sticky top-0 z-20 bg-background font-bold underline">{t("columnTeam")}</TableHead>
                  <TableHead className="sticky top-0 z-20 bg-background font-bold underline">{t("columnTransportType")}</TableHead>
                  <TableHead className="sticky top-0 z-20 bg-background font-bold underline">{t("columnStatus")}</TableHead>
                  <TableHead className="sticky top-0 z-20 bg-background font-bold underline">{t("columnFestival")}</TableHead>
                  <TableHead className="sticky top-0 z-20 bg-background font-bold underline">{t("columnDeliveryDate")}</TableHead>
                </TableRow>
                {/* The filter row: each control sits directly under the column it filters. */}
                <TableRow>
                  <TableHead className="sticky top-10 z-20 bg-background" />
                  {(
                    [
                      ["location", "filterLocation"],
                      ["karNummer", "filterKarNummer"],
                      ["team", "filterTeam"],
                      ["transportType", "filterTransportType"],
                    ] as const
                  ).map(([key, label]) => (
                    <TableHead key={key} className="sticky top-10 z-20 bg-background">
                      <Input
                        aria-label={t(label)}
                        placeholder={t(label)}
                        className="h-8 w-full min-w-28 font-normal"
                        value={textFilters[key]}
                        onChange={(event) => setTextFilter(key, event.target.value)}
                      />
                    </TableHead>
                  ))}
                  <TableHead className="sticky top-10 z-20 bg-background">
                    <Select value={statusFilter} onValueChange={(value) => setStatusFilter(value ?? ALL_STATUSES)}>
                      <SelectTrigger aria-label={t("filterStatus")} className="h-8 w-full min-w-36 font-normal">
                        <SelectValue>
                          {(value: string | null) => (value && value !== ALL_STATUSES ? value : t("allStatuses"))}
                        </SelectValue>
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value={ALL_STATUSES}>{t("allStatuses")}</SelectItem>
                        {statusOptions.map((status) => (
                          <SelectItem key={status} value={status}>
                            {status}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </TableHead>
                  {(
                    [
                      ["festival", "filterFestival"],
                      ["deliveryDate", "filterDeliveryDate"],
                    ] as const
                  ).map(([key, label]) => (
                    <TableHead key={key} className="sticky top-10 z-20 bg-background">
                      <Input
                        aria-label={t(label)}
                        placeholder={t(label)}
                        className="h-8 w-full min-w-28 font-normal"
                        value={textFilters[key]}
                        onChange={(event) => setTextFilter(key, event.target.value)}
                      />
                    </TableHead>
                  ))}
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredGroups.length === 0 && (
                  <TableRow>
                    <TableCell colSpan={COLUMN_COUNT} className="py-6 text-center text-muted-foreground">
                      {t("noFilterResults")}
                    </TableCell>
                  </TableRow>
                )}
                {filteredGroups.map((distributiepunt) => {
                  const distributiepuntKarIds = distributiepunt.locations.flatMap((location) =>
                    location.karren.map((kar) => kar.id),
                  );
                  const distributiepuntState = groupState(distributiepuntKarIds, selectedIds);
                  return (
                    <Fragment key={distributiepunt.id}>
                      {/* The distributiepunt: checkbox for all its karren, name + number of karren. */}
                      <TableRow className="bg-purple-100 text-purple-800 hover:bg-purple-100 dark:bg-purple-500/15 dark:text-purple-200 dark:hover:bg-purple-500/15">
                        <TableCell>
                          <Checkbox
                            checked={distributiepuntState.checked}
                            indeterminate={distributiepuntState.indeterminate}
                            onCheckedChange={(checked) => setMany(distributiepuntKarIds, checked === true)}
                            aria-label={t("selectGroup", { name: distributiepunt.name })}
                          />
                        </TableCell>
                        <TableCell colSpan={COLUMN_COUNT - 1}>
                          <div className="flex items-center gap-3">
                            <span className="text-base font-bold">{distributiepunt.name}</span>
                            <span className="ml-auto font-bold">{t("karCount", { count: distributiepunt.count })}</span>
                          </div>
                        </TableCell>
                      </TableRow>
                      {distributiepunt.locations.map((location) => {
                        const locationKarIds = location.karren.map((kar) => kar.id);
                        const locationState = groupState(locationKarIds, selectedIds);
                        return (
                          <Fragment key={location.id}>
                            {/* The location: checkbox, tour position, description/name, zone, count. */}
                            <TableRow className="bg-muted/60 hover:bg-muted/60">
                              <TableCell>
                                <Checkbox
                                  checked={locationState.checked}
                                  indeterminate={locationState.indeterminate}
                                  onCheckedChange={(checked) => setMany(locationKarIds, checked === true)}
                                  aria-label={t("selectGroup", { name: location.name })}
                                />
                              </TableCell>
                              <TableCell colSpan={COLUMN_COUNT - 1} className="pl-6">
                                <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
                                  {location.terrein_positie !== null ? (
                                    <span className="text-base font-bold">
                                      {t("position", { position: location.terrein_positie })}
                                    </span>
                                  ) : (
                                    <Badge variant="outline" className="text-muted-foreground">
                                      {t("noPosition")}
                                    </Badge>
                                  )}
                                  <span className="font-semibold">
                                    {location.description ? `${location.name} — ${location.description}` : location.name}
                                  </span>
                                  <span className="text-muted-foreground">{t("zone", { zone: location.zone_name })}</span>
                                  {!location.active && (
                                    <Badge variant="outline" className="text-muted-foreground">
                                      {t("inactive")}
                                    </Badge>
                                  )}
                                  <span className="ml-auto font-semibold">
                                    {t("karCount", { count: location.karren.length })}
                                  </span>
                                </div>
                              </TableCell>
                            </TableRow>
                            {/* The karren delivered there, by kar number. */}
                            {location.karren.map((kar) => (
                              <TableRow key={kar.id} data-state={selectedIds.has(kar.id) ? "selected" : undefined}>
                                <TableCell onClickCapture={rememberShift}>
                                  <Checkbox
                                    checked={selectedIds.has(kar.id)}
                                    onCheckedChange={(checked) => toggleKar(kar.id, checked === true)}
                                    aria-label={t("selectKar", { kar: kar.kar_nummer })}
                                  />
                                </TableCell>
                                <TableCell />
                                <TableCell className="font-medium">{kar.kar_nummer}</TableCell>
                                <TableCell>{kar.team_name}</TableCell>
                                <TableCell>{kar.transport_type_name}</TableCell>
                                <TableCell>
                                  <Badge className={statusPillClassName(kar.status_name)}>{kar.status_name}</Badge>
                                </TableCell>
                                <TableCell>{kar.festival_name}</TableCell>
                                <TableCell>{formatDateNl(kar.delivery_date)}</TableCell>
                              </TableRow>
                            ))}
                          </Fragment>
                        );
                      })}
                    </Fragment>
                  );
                })}
              </TableBody>
            </Table>
          </div>
        </>
      )}
    </div>
  );
}
