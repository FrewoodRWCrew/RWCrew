"use client";

// KarTracker's "Verplaatsingen tussen festivals" screen (Planningsanalyses
// group): for the season selected in the header and a chosen festival pair
// ("Van" A -> "Naar" B), which karren have to be moved on the ground because
// their team's planned delivery location differs between the two — see
// module_2/kar_moves_service.py for the rule. The dropdowns list the season's
// active festivals in calendar order and start on the first two.
//
// The table is grouped per pick-up location (where the karren stand at A; a
// purple header row, in the order of the delivery tour "Leveringsvolgorde",
// locations without a position last), followed by its karren with the
// location they have to go to.
//
// Every kar line has a checkbox; Shift-click ticks (or unticks) the whole
// range since the previous click, and the checkbox on a pick-up location
// does all its karren at once. "Print verplaatsingen" turns the ticked
// karren into a landscape PDF for the drivers (module_2/kar_moves_pdf.py),
// optionally with a map page showing every move as an arrow.
//
// A filter row under the column headings narrows the karren shown: a dropdown
// for Status, free text for the other columns (the Van/Naar filters match the
// location's position, name, description and zone). Locations without a
// matching kar disappear; "select all", the group checkboxes and Shift ranges
// only touch the karren shown. Ticked karren stay ticked when a filter hides them.

import { Fragment, useEffect, useMemo, useRef, useState, type MouseEvent } from "react";
import { useLocale, useTranslations } from "next-intl";
import { toast } from "sonner";
import { getKarMoves, printKarMoves } from "@/lib/api";
import { formatDateNl } from "@/lib/date-time";
import { useSelectedSeason } from "@/components/shared/season-provider";
import { statusPillClassName } from "@/components/module-2/status-colour";
import type { KarTrackerKarMoves, KarTrackerKarMovesLocation } from "@/lib/types";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";

// The number of columns (checkbox included), so a header row can span all of them.
const COLUMN_COUNT = 7;

// The festival pair chosen in the dropdowns, remembered with its season so
// another season starts again on its own first two festivals.
interface FestivalChoice {
  seasonId: number | null;
  fromId: number | null;
  toId: number | null;
}

// The moves fetched for one season + festival pair, remembered together with them.
interface LoadedMoves {
  key: string;
  seasonId: number;
  moves: KarTrackerKarMoves;
}

// The ticked karren, remembered with the season + pair they belong to so
// another choice starts with nothing ticked.
interface Selection {
  key: string;
  ids: Set<number>;
}

// The free-text column filters (Status has its own dropdown).
interface TextFilters {
  from: string;
  karNummer: string;
  team: string;
  transportType: string;
  to: string;
}

const EMPTY_TEXT_FILTERS: TextFilters = { from: "", karNummer: "", team: "", transportType: "", to: "" };

// The Status dropdown's "no filter" value.
const ALL_STATUSES = "__all__";

/** Case-insensitive substring match; an empty filter matches everything. */
function textMatches(fieldValue: string | null, filterValue: string): boolean {
  if (!filterValue) return true;
  return (fieldValue ?? "").toLowerCase().includes(filterValue.trim().toLowerCase());
}

/** The text a Van/Naar filter searches in: position, name, description and zone. */
function locationText(location: KarTrackerKarMovesLocation): string {
  return [location.terrein_positie, location.name, location.description, location.zone_name]
    .filter((part) => part !== null)
    .join(" ");
}

// What a group checkbox shows for its karren: all, some or none ticked.
function groupState(karIds: number[], selected: Set<number>): { checked: boolean; indeterminate: boolean } {
  const count = karIds.filter((id) => selected.has(id)).length;
  return { checked: count > 0 && count === karIds.length, indeterminate: count > 0 && count < karIds.length };
}

export function KarMovesScreen() {
  const t = useTranslations("karTracker.karMoves");
  const locale = useLocale();
  const { selectedSeasonId } = useSelectedSeason();

  const [choice, setChoice] = useState<FestivalChoice>({ seasonId: null, fromId: null, toId: null });
  const [loaded, setLoaded] = useState<LoadedMoves | null>(null);
  const [selection, setSelection] = useState<Selection>({ key: "", ids: new Set() });
  const [includeMap, setIncludeMap] = useState(false);
  const [textFilters, setTextFilters] = useState<TextFilters>(EMPTY_TEXT_FILTERS);
  const [statusFilter, setStatusFilter] = useState(ALL_STATUSES);
  // True while the PDF is being generated, so the button can't be clicked twice.
  const [printing, setPrinting] = useState(false);
  // The kar clicked last (start of a Shift range) and whether the click that
  // is being handled had Shift held (Base UI's change event has no modifier keys).
  const anchorRef = useRef<number | null>(null);
  const shiftRef = useRef(false);

  // The chosen pair only counts for the season it was made in.
  const fromId = choice.seasonId === selectedSeasonId ? choice.fromId : null;
  const toId = choice.seasonId === selectedSeasonId ? choice.toId : null;
  const currentKey = `${selectedSeasonId}:${fromId}:${toId}`;

  // (Re)load whenever the season or the pair changes. Without a pair the
  // answer only holds the festivals: then the first two are picked, which
  // loads again with that pair. The `cancelled` flag drops a response that
  // arrives after the choice already changed again.
  useEffect(() => {
    if (selectedSeasonId === null) return;
    let cancelled = false;

    getKarMoves(selectedSeasonId, fromId, toId)
      .then((moves) => {
        if (cancelled) return;
        setLoaded({ key: `${selectedSeasonId}:${fromId}:${toId}`, seasonId: selectedSeasonId, moves });
        if (fromId === null && toId === null && moves.festivals.length >= 2) {
          setChoice({ seasonId: selectedSeasonId, fromId: moves.festivals[0].id, toId: moves.festivals[1].id });
        }
      })
      .catch(() => {
        if (!cancelled) toast.error(t("loadError"));
      });

    return () => {
      cancelled = true;
    };
  }, [selectedSeasonId, fromId, toId, t]);

  // The dropdowns' festivals (of the season shown); the moves of the current
  // pair only (another pair's rows would be misleading while the new one loads).
  const festivals = loaded !== null && loaded.seasonId === selectedSeasonId ? loaded.moves.festivals : [];
  const moves = loaded !== null && loaded.key === currentKey && fromId !== null ? loaded.moves : null;
  // Ticks only count for the season + pair they were made in.
  const selectedIds = useMemo(
    () => (selection.key === currentKey ? selection.ids : new Set<number>()),
    [selection, currentKey],
  );

  // The statuses in these moves, for the Status dropdown.
  const statusOptions = useMemo(
    () =>
      [
        ...new Set(moves?.locations.flatMap((location) => location.karren.map((kar) => kar.status_name)) ?? []),
      ].sort((a, b) => a.localeCompare(b)),
    [moves],
  );

  const anyFilterSet = statusFilter !== ALL_STATUSES || Object.values(textFilters).some((value) => value !== "");

  // The moves with only the karren matching every filter; pick-up locations
  // left empty drop out.
  const filteredLocations = useMemo(() => {
    if (moves === null) return [];
    return moves.locations.flatMap((location) => {
      if (!textMatches(locationText(location), textFilters.from)) return [];
      const karren = location.karren.filter(
        (kar) =>
          (statusFilter === ALL_STATUSES || kar.status_name === statusFilter) &&
          textMatches(kar.kar_nummer, textFilters.karNummer) &&
          textMatches(kar.team_name, textFilters.team) &&
          textMatches(kar.transport_type_name, textFilters.transportType) &&
          textMatches(locationText(kar.to_location), textFilters.to),
      );
      return karren.length > 0 ? [{ ...location, karren }] : [];
    });
  }, [moves, textFilters, statusFilter]);

  // Every kar id shown, in screen order (the order a Shift range runs in).
  const allKarIds = useMemo(
    () => filteredLocations.flatMap((location) => location.karren.map((kar) => kar.id)),
    [filteredLocations],
  );

  /** Picks the "Van" or "Naar" festival. */
  function chooseFestival(side: "fromId" | "toId", value: string | null) {
    if (value === null || selectedSeasonId === null) return;
    setChoice({ seasonId: selectedSeasonId, fromId, toId, [side]: Number(value) });
  }

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
    setSelection({ key: currentKey, ids: next });
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
    if (selectedSeasonId === null || fromId === null || toId === null || selectedIds.size === 0) return;

    setPrinting(true);
    try {
      const pdf = await printKarMoves(selectedSeasonId, fromId, toId, [...selectedIds], includeMap, locale);
      // Show the PDF in a new tab (the browser's viewer has the print
      // dialog); the object URL is released after the tab has had time to load it.
      const url = URL.createObjectURL(pdf);
      if (!window.open(url, "_blank")) {
        // The browser blocked the pop-up (it opened after an async call), so
        // hand the PDF over as a normal download instead.
        const link = document.createElement("a");
        link.href = url;
        link.download = "Verplaatsingen.pdf";
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

  /** "#3 Poort — description" (or a "geen positie" badge) + zone, for a pick-up or destination. */
  function renderLocation(location: KarTrackerKarMovesLocation, bold: boolean) {
    return (
      <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
        {location.terrein_positie !== null ? (
          <span className={bold ? "text-base font-bold" : "font-semibold"}>
            {t("position", { position: location.terrein_positie })}
          </span>
        ) : (
          <Badge variant="outline" className="text-muted-foreground">
            {t("noPosition")}
          </Badge>
        )}
        <span className={bold ? "font-bold" : "font-medium"}>
          {location.description ? `${location.name} — ${location.description}` : location.name}
        </span>
        <span className="text-muted-foreground">{t("zone", { zone: location.zone_name })}</span>
        {!location.active && (
          <Badge variant="outline" className="text-muted-foreground">
            {t("inactive")}
          </Badge>
        )}
      </div>
    );
  }

  /** One festival dropdown; the festival chosen on the other side can't be picked. */
  function renderFestivalSelect(side: "fromId" | "toId", label: string, otherId: number | null) {
    const value = side === "fromId" ? fromId : toId;
    return (
      <div className="flex flex-col gap-1.5">
        <Label>{label}</Label>
        <Select value={value === null ? null : String(value)} onValueChange={(next) => chooseFestival(side, next)}>
          <SelectTrigger aria-label={label} className="w-56">
            <SelectValue>
              {(selected: string | null) => festivals.find((festival) => String(festival.id) === selected)?.name ?? ""}
            </SelectValue>
          </SelectTrigger>
          <SelectContent>
            {festivals.map((festival) => (
              <SelectItem key={festival.id} value={String(festival.id)} disabled={festival.id === otherId}>
                {festival.name} ({formatDateNl(festival.start_date)})
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight underline">{t("title")}</h1>
          <p className="text-muted-foreground">{t("description")}</p>
        </div>
        {/* Print the ticked karren, optionally with the map page. */}
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <Checkbox
              id="kar-moves-include-map"
              checked={includeMap}
              onCheckedChange={(checked) => setIncludeMap(checked === true)}
            />
            <Label htmlFor="kar-moves-include-map">{t("includeMap")}</Label>
          </div>
          <Button onClick={handlePrint} disabled={selectedIds.size === 0 || printing}>
            {printing ? t("printing") : t("printButton")}
          </Button>
        </div>
      </div>

      {selectedSeasonId === null ? (
        <p className="text-sm text-muted-foreground">{t("noSeason")}</p>
      ) : loaded === null || loaded.seasonId !== selectedSeasonId ? (
        <p className="text-sm text-muted-foreground">{t("loading")}</p>
      ) : festivals.length < 2 ? (
        <p className="text-sm text-muted-foreground">{t("notEnoughFestivals")}</p>
      ) : (
        <>
          {/* The festival pair. */}
          <div className="flex flex-wrap items-end gap-4">
            {renderFestivalSelect("fromId", t("fromFestival"), toId)}
            <span className="pb-2 text-muted-foreground">→</span>
            {renderFestivalSelect("toId", t("toFestival"), fromId)}
            {moves?.to_delivery_date && (
              <span className="pb-2 text-sm text-muted-foreground">
                {t("deliveryDate", { date: formatDateNl(moves.to_delivery_date) })}
              </span>
            )}
          </div>

          {moves === null ? (
            <p className="text-sm text-muted-foreground">{t("loading")}</p>
          ) : moves.locations.length === 0 ? (
            <p className="text-sm text-muted-foreground">{t("empty")}</p>
          ) : (
            <>
              {/* The total; the shown/selection counts on the right. */}
              <div className="flex flex-wrap items-center gap-2 text-sm">
                <span className="font-semibold">{t("total", { count: moves.total })}</span>
                <span className="ml-auto text-muted-foreground">
                  {t("shownCount", { shown: allKarIds.length, total: moves.total })} ·{" "}
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
                      <TableHead className="sticky top-0 z-20 bg-background font-bold underline">{t("columnFrom")}</TableHead>
                      <TableHead className="sticky top-0 z-20 bg-background font-bold underline">{t("columnKarNummer")}</TableHead>
                      <TableHead className="sticky top-0 z-20 bg-background font-bold underline">{t("columnTeam")}</TableHead>
                      <TableHead className="sticky top-0 z-20 bg-background font-bold underline">{t("columnTransportType")}</TableHead>
                      <TableHead className="sticky top-0 z-20 bg-background font-bold underline">{t("columnStatus")}</TableHead>
                      <TableHead className="sticky top-0 z-20 bg-background font-bold underline">{t("columnTo")}</TableHead>
                    </TableRow>
                    {/* The filter row: each control sits directly under the column it filters. */}
                    <TableRow>
                      <TableHead className="sticky top-10 z-20 bg-background" />
                      {(
                        [
                          ["from", "filterFrom"],
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
                      <TableHead className="sticky top-10 z-20 bg-background">
                        <Input
                          aria-label={t("filterTo")}
                          placeholder={t("filterTo")}
                          className="h-8 w-full min-w-28 font-normal"
                          value={textFilters.to}
                          onChange={(event) => setTextFilter("to", event.target.value)}
                        />
                      </TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {filteredLocations.length === 0 && (
                      <TableRow>
                        <TableCell colSpan={COLUMN_COUNT} className="py-6 text-center text-muted-foreground">
                          {t("noFilterResults")}
                        </TableCell>
                      </TableRow>
                    )}
                    {filteredLocations.map((location) => {
                      const locationKarIds = location.karren.map((kar) => kar.id);
                      const locationState = groupState(locationKarIds, selectedIds);
                      return (
                        <Fragment key={location.id}>
                          {/* The pick-up location: checkbox, tour position, name, zone, count. */}
                          <TableRow className="bg-purple-100 text-purple-800 hover:bg-purple-100 dark:bg-purple-500/15 dark:text-purple-200 dark:hover:bg-purple-500/15">
                            <TableCell>
                              <Checkbox
                                checked={locationState.checked}
                                indeterminate={locationState.indeterminate}
                                onCheckedChange={(checked) => setMany(locationKarIds, checked === true)}
                                aria-label={t("selectGroup", { name: location.name })}
                              />
                            </TableCell>
                            <TableCell colSpan={COLUMN_COUNT - 1}>
                              <div className="flex flex-wrap items-center gap-3">
                                <span className="text-xs font-semibold uppercase">{t("pickUpAt")}</span>
                                {renderLocation(location, true)}
                                <span className="ml-auto font-bold">{t("karCount", { count: location.karren.length })}</span>
                              </div>
                            </TableCell>
                          </TableRow>
                          {/* The karren to take away from there, by kar number, with their destination. */}
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
                              <TableCell>{renderLocation(kar.to_location, false)}</TableCell>
                            </TableRow>
                          ))}
                        </Fragment>
                      );
                    })}
                  </TableBody>
                </Table>
              </div>
            </>
          )}
        </>
      )}
    </div>
  );
}
