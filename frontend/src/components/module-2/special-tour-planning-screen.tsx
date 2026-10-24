"use client";

// KarTracker's "Speciale levertoeren-planning" screen (Planningsanalyses
// group): for the season selected in the header, a chosen festival and one or
// more special delivery tours (KarTracker "Speciale levertoeren", linked to
// teams on MasterData's team fiche), which karren the tours pass by and where
// they stand — see module_2/special_tour_planning_service.py for the rule (the
// location planned for the kar's team at that festival).
//
// The table lists the tour's stops (a purple header row per delivery
// location, "Stop 1..n" in the order of the delivery tour) followed by the
// karren standing there; no distributiepunten, the tour passes by the karren.
// A kar on two of the selected tours is listed once with both tour names in
// "Levertoer". Checkboxes with Shift ranges, the filter row and "Print
// leverplanning" (module_2/special_tour_pdf.py, optionally with the route map)
// work like "Initiële leverplanning". The festival dropdown starts on the
// season's first festival; no tour is selected until the user picks one.

import { Fragment, useEffect, useMemo, useRef, useState, type MouseEvent } from "react";
import { useLocale, useTranslations } from "next-intl";
import { toast } from "sonner";
import { getSpecialTourPlanning, printSpecialTourPlanning } from "@/lib/api";
import { formatDateNl } from "@/lib/date-time";
import { useSelectedSeason } from "@/components/shared/season-provider";
import { statusPillClassName } from "@/components/module-2/status-colour";
import type { KarTrackerSpecialTourPlanning } from "@/lib/types";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { TagMultiSelect } from "@/components/ui/tag-multi-select";

// The number of columns (checkbox included), so a header row can span all of them.
const COLUMN_COUNT = 8;

// The festival + tours chosen above the table, remembered with their season
// so another season starts again on its own first festival.
interface PlanningChoice {
  seasonId: number | null;
  festivalId: number | null;
  tourIds: number[];
}

// A planning fetched for one season + festival + tours, remembered together with them.
interface LoadedPlanning {
  key: string;
  seasonId: number;
  planning: KarTrackerSpecialTourPlanning;
}

// The ticked karren, remembered with the choice they belong to so another
// choice starts with nothing ticked.
interface Selection {
  key: string;
  ids: Set<number>;
}

// The free-text column filters (Status has its own dropdown).
interface TextFilters {
  location: string;
  karNummer: string;
  team: string;
  transportType: string;
  tour: string;
  deliveryDate: string;
}

const EMPTY_TEXT_FILTERS: TextFilters = {
  location: "",
  karNummer: "",
  team: "",
  transportType: "",
  tour: "",
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

export function SpecialTourPlanningScreen() {
  const t = useTranslations("karTracker.specialTourPlanning");
  const locale = useLocale();
  const { selectedSeasonId } = useSelectedSeason();

  const [choice, setChoice] = useState<PlanningChoice>({ seasonId: null, festivalId: null, tourIds: [] });
  const [loaded, setLoaded] = useState<LoadedPlanning | null>(null);
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

  // The choice only counts for the season it was made in.
  const sameSeason = choice.seasonId === selectedSeasonId;
  const festivalId = sameSeason ? choice.festivalId : null;
  const tourIds = useMemo(() => (sameSeason ? choice.tourIds : []), [sameSeason, choice.tourIds]);
  const currentKey = `${selectedSeasonId}:${festivalId}:${[...tourIds].sort((a, b) => a - b).join(",")}`;

  // (Re)load whenever the season, festival or tours change. Without a
  // festival the answer only holds the filter data: then the first festival
  // is picked, which loads again. The `cancelled` flag drops a response that
  // arrives after the choice already changed again.
  useEffect(() => {
    if (selectedSeasonId === null) return;
    let cancelled = false;
    const key = currentKey;

    getSpecialTourPlanning(selectedSeasonId, festivalId, tourIds)
      .then((planning) => {
        if (cancelled) return;
        setLoaded({ key, seasonId: selectedSeasonId, planning });
        if (festivalId === null && planning.festivals.length > 0) {
          setChoice({ seasonId: selectedSeasonId, festivalId: planning.festivals[0].id, tourIds });
        }
      })
      .catch(() => {
        if (!cancelled) toast.error(t("loadError"));
      });

    return () => {
      cancelled = true;
    };
  }, [selectedSeasonId, festivalId, tourIds, currentKey, t]);

  // The filters' festivals and tours (of the season shown); the planning of
  // the current choice only (another choice's rows would mislead while loading).
  const filterData = loaded !== null && loaded.seasonId === selectedSeasonId ? loaded.planning : null;
  const planning = loaded !== null && loaded.key === currentKey && festivalId !== null ? loaded.planning : null;
  // Ticks only count for the choice they were made in.
  const selectedIds = useMemo(
    () => (selection.key === currentKey ? selection.ids : new Set<number>()),
    [selection, currentKey],
  );

  // The statuses in this planning, for the Status dropdown.
  const statusOptions = useMemo(
    () =>
      [
        ...new Set(planning?.locations.flatMap((location) => location.karren.map((kar) => kar.status_name)) ?? []),
      ].sort((a, b) => a.localeCompare(b)),
    [planning],
  );

  const anyFilterSet = statusFilter !== ALL_STATUSES || Object.values(textFilters).some((value) => value !== "");

  // The stops with only the karren matching every filter; stops left empty drop out.
  const filteredStops = useMemo(() => {
    if (planning === null) return [];
    return planning.locations.flatMap((location) => {
      const locationText = [location.stop, location.name, location.description, location.zone_name].join(" ");
      if (!textMatches(locationText, textFilters.location)) return [];
      const karren = location.karren.filter(
        (kar) =>
          (statusFilter === ALL_STATUSES || kar.status_name === statusFilter) &&
          textMatches(kar.kar_nummer, textFilters.karNummer) &&
          textMatches(kar.team_name, textFilters.team) &&
          textMatches(kar.transport_type_name, textFilters.transportType) &&
          textMatches((kar.tour_names ?? []).join(", "), textFilters.tour) &&
          textMatches(formatDateNl(kar.delivery_date), textFilters.deliveryDate),
      );
      return karren.length > 0 ? [{ ...location, karren }] : [];
    });
  }, [planning, textFilters, statusFilter]);

  // Every kar id shown, in screen order (the order a Shift range runs in).
  const allKarIds = useMemo(
    () => filteredStops.flatMap((location) => location.karren.map((kar) => kar.id)),
    [filteredStops],
  );

  /** Picks the festival (keeping the chosen tours). */
  function chooseFestival(value: string | null) {
    if (value === null || selectedSeasonId === null) return;
    setChoice({ seasonId: selectedSeasonId, festivalId: Number(value), tourIds });
  }

  /** Sets the selected tours (keeping the festival). */
  function chooseTours(ids: number[]) {
    if (selectedSeasonId === null) return;
    setChoice({ seasonId: selectedSeasonId, festivalId, tourIds: ids });
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
    if (selectedSeasonId === null || festivalId === null || tourIds.length === 0 || selectedIds.size === 0) return;

    setPrinting(true);
    try {
      const pdf = await printSpecialTourPlanning(
        selectedSeasonId,
        festivalId,
        tourIds,
        [...selectedIds],
        includeMap,
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
        link.download = "Leverplanning-speciale-levertoeren.pdf";
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
  const festivals = filterData?.festivals ?? [];
  const tourOptions = (filterData?.tours ?? []).map((tour) => ({ id: tour.id, label: tour.name }));

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
              id="special-tour-planning-include-map"
              checked={includeMap}
              onCheckedChange={(checked) => setIncludeMap(checked === true)}
            />
            <Label htmlFor="special-tour-planning-include-map">{t("includeMap")}</Label>
          </div>
          <Button onClick={handlePrint} disabled={selectedIds.size === 0 || printing}>
            {printing ? t("printing") : t("printButton")}
          </Button>
        </div>
      </div>

      {selectedSeasonId === null ? (
        <p className="text-sm text-muted-foreground">{t("noSeason")}</p>
      ) : filterData === null ? (
        <p className="text-sm text-muted-foreground">{t("loading")}</p>
      ) : festivals.length === 0 ? (
        <p className="text-sm text-muted-foreground">{t("noFestivals")}</p>
      ) : (
        <>
          {/* The festival and the tours to show. */}
          <div className="flex flex-wrap items-end gap-4">
            <div className="flex flex-col gap-1.5">
              <Label>{t("festival")}</Label>
              <Select value={festivalId === null ? null : String(festivalId)} onValueChange={chooseFestival}>
                <SelectTrigger aria-label={t("festival")} className="w-56">
                  <SelectValue>
                    {(selected: string | null) =>
                      festivals.find((festival) => String(festival.id) === selected)?.name ?? ""
                    }
                  </SelectValue>
                </SelectTrigger>
                <SelectContent>
                  {festivals.map((festival) => (
                    <SelectItem key={festival.id} value={String(festival.id)}>
                      {festival.name} ({formatDateNl(festival.start_date)})
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="flex min-w-72 flex-1 flex-col gap-1.5">
              <Label htmlFor="special-tour-planning-tours">{t("tours")}</Label>
              <TagMultiSelect
                id="special-tour-planning-tours"
                options={tourOptions}
                selectedIds={tourIds}
                onChange={chooseTours}
                placeholder={t("toursPlaceholder")}
              />
            </div>
            {planning?.delivery_date && (
              <span className="pb-2 text-sm text-muted-foreground">
                {t("deliveryDate", { date: formatDateNl(planning.delivery_date) })}
              </span>
            )}
          </div>

          {tourOptions.length === 0 ? (
            <p className="text-sm text-muted-foreground">{t("noTours")}</p>
          ) : tourIds.length === 0 ? (
            <p className="text-sm text-muted-foreground">{t("chooseTours")}</p>
          ) : planning === null ? (
            <p className="text-sm text-muted-foreground">{t("loading")}</p>
          ) : planning.locations.length === 0 ? (
            <p className="text-sm text-muted-foreground">{t("empty")}</p>
          ) : (
            <>
              {/* The totals: karren and stops; the selection count on the right. */}
              <div className="flex flex-wrap items-center gap-2 text-sm">
                <span className="font-semibold">{t("total", { count: planning.total })}</span>
                <span className="text-muted-foreground">· {t("stopCount", { count: planning.locations.length })}</span>
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
                      <TableHead className="sticky top-0 z-20 bg-background font-bold underline">{t("columnTour")}</TableHead>
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
                          ["tour", "filterTour"],
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
                    {filteredStops.length === 0 && (
                      <TableRow>
                        <TableCell colSpan={COLUMN_COUNT} className="py-6 text-center text-muted-foreground">
                          {t("noFilterResults")}
                        </TableCell>
                      </TableRow>
                    )}
                    {filteredStops.map((location) => {
                      const locationKarIds = location.karren.map((kar) => kar.id);
                      const locationState = groupState(locationKarIds, selectedIds);
                      return (
                        <Fragment key={location.id}>
                          {/* The stop: checkbox, stop number, description/name, zone, tour position, count. */}
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
                              <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
                                <span className="text-base font-bold">{t("stop", { stop: location.stop })}</span>
                                <span className="font-semibold">
                                  {location.description ? `${location.name} — ${location.description}` : location.name}
                                </span>
                                <span className="opacity-80">{t("zone", { zone: location.zone_name })}</span>
                                {location.terrein_positie === null && (
                                  <Badge variant="outline" className="text-muted-foreground">
                                    {t("noPosition")}
                                  </Badge>
                                )}
                                {!location.active && (
                                  <Badge variant="outline" className="text-muted-foreground">
                                    {t("inactive")}
                                  </Badge>
                                )}
                                <span className="ml-auto font-bold">{t("karCount", { count: location.karren.length })}</span>
                              </div>
                            </TableCell>
                          </TableRow>
                          {/* The karren standing there, by kar number. */}
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
                              <TableCell>{(kar.tour_names ?? []).join(", ")}</TableCell>
                              <TableCell>{formatDateNl(kar.delivery_date)}</TableCell>
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
