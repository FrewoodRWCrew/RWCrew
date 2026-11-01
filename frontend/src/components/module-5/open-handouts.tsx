"use client";

// Atelier's "Balie > Openstaand" screen: the pieces that were picked up and
// not brought back yet, grouped per team (ploeg), then per person (with
// bracelet number; no email column, for privacy — GDPR), then one line per piece with
// its festival day and since when. Filters: festival + day at the top (they
// decide what's loaded) and a text filter above every column (client-side).
// The Excel button downloads the pieces shown, without email addresses.
// With the desk's rights, a person's "Inname" button opens the desk's return
// form in a dialog, so the list can be worked through without leaving it.
// With the write-off right, a person's "Afboeken" button closes the pieces that
// never come back (desk-write-off-dialog.tsx).

import { Fragment, useMemo, useState } from "react";
import { Download, PackageMinus, PackageX } from "lucide-react";
import { useLocale, useTranslations } from "next-intl";
import { toast } from "sonner";
import { exportAtelierOpenHandouts, listAtelierOpenHandouts } from "@/lib/api";
import { formatDateNl, formatDateTimeNl } from "@/lib/date-time";
import type { AtelierHandout, Season } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import { SearchableSelect } from "@/components/ui/searchable-select";
import { Table, TableBody, TableCell, TableFooter, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { AtelierFestivalSelect, useAtelierFestival } from "@/components/module-5/atelier-festival-select";
import { AtelierSeasonSelect, useAtelierSeasonId } from "@/components/module-5/atelier-season-select";
import { ATELIER_STOCK_CHANGED_EVENT } from "@/components/module-5/atelier-stock-common";
import { FilterHeadCell, useColumnFilters } from "@/components/module-5/column-filters";
import { saveExcel } from "@/components/module-5/desk-common";
import { ReturnForm } from "@/components/module-5/desk-return-form";
import { WriteOffDialog } from "@/components/module-5/desk-write-off-dialog";
import { useKeyedLoad } from "@/components/module-4/use-keyed-load";

// The day filter's "every day" choice (Base UI's Select needs a non-empty value).
const ALL = "all";

// The table's columns, in order (each has a text filter above it).
const COLUMNS = ["team", "person", "bracelet", "day", "article", "size", "since"] as const;
type Column = (typeof COLUMNS)[number];

// One open piece, with the texts its columns show (and filter on).
interface PieceRow {
  key: string;
  lineId: number;
  teamName: string;
  personId: number;
  personName: string;
  bracelet: string | null;
  day: string;
  article: string;
  size: string;
  since: string;
}

// A person with their open pieces, and a team with its persons.
interface PersonGroup {
  personId: number;
  personName: string;
  bracelet: string | null;
  pieces: PieceRow[];
}
interface TeamGroup {
  teamName: string;
  persons: PersonGroup[];
  pieces: number;
}

interface OpenHandoutsProps {
  seasons: Season[];
  /** May book a return (shows the Actions column with "Inname"). */
  canBook: boolean;
  /** May cancel a pick-up in the Inname dialog. */
  canCancel: boolean;
  /** May write off pieces that never come back (shows "Afboeken"). */
  canWriteOff: boolean;
}

export function OpenHandouts({ seasons, canBook, canCancel, canWriteOff }: OpenHandoutsProps) {
  const t = useTranslations("atelier.open");
  const tFit = useTranslations("atelier.fits");
  const locale = useLocale();
  const seasonId = useAtelierSeasonId(seasons);
  const { festivals, festival } = useAtelierFestival(seasonId);
  const [day, setDay] = useState<string>(ALL);
  const { filters, setFilter, matches, active } = useColumnFilters<Column>();
  const [isDownloading, setIsDownloading] = useState(false);
  // The person whose Inname dialog is open.
  const [returnPerson, setReturnPerson] = useState<PersonGroup | null>(null);
  // The person whose Afboeken dialog is open.
  const [writeOffPerson, setWriteOffPerson] = useState<PersonGroup | null>(null);
  // The table's width in columns, with the Actions column when it's shown.
  const hasActions = canBook || canWriteOff;
  const columnCount = COLUMNS.length + (hasActions ? 1 : 0);

  const key = festival ? `${festival.id}-${day}` : null;
  const rows = useKeyedLoad<AtelierHandout[]>(key, () =>
    listAtelierOpenHandouts({ festivalId: festival!.id, day: day === ALL ? null : day, teamId: null }),
  );

  // Every open piece as one row, sorted by team, person, day and article.
  const pieces = useMemo<PieceRow[]>(() => {
    const list = (rows.data ?? []).flatMap((handout) =>
      handout.lines
        .filter((line) => line.returned_at === null)
        .map((line) => ({
          key: `${handout.id}-${line.id}`,
          lineId: line.id,
          teamName: handout.team_name,
          personId: handout.person_id,
          personName: handout.person_name,
          bracelet: handout.bracelet_number,
          day: handout.day,
          article: line.article_name,
          size: `${line.size_name} · ${tFit(line.fit)}`,
          since: handout.created_at,
        })),
    );
    return list.sort(
      (a, b) =>
        a.teamName.localeCompare(b.teamName) ||
        a.personName.localeCompare(b.personName) ||
        a.day.localeCompare(b.day) ||
        a.article.localeCompare(b.article),
    );
  }, [rows.data, tFit]);

  // The pieces matching every column filter (dates matched as shown on screen).
  const shown = pieces.filter((piece) =>
    matches({
      team: piece.teamName,
      person: piece.personName,
      bracelet: piece.bracelet,
      day: formatDateNl(piece.day),
      article: piece.article,
      size: piece.size,
      since: formatDateTimeNl(piece.since),
    }),
  );

  // Group the shown pieces per team, then per person (already sorted that way).
  const teams: TeamGroup[] = [];
  for (const piece of shown) {
    let team = teams.at(-1);
    if (!team || team.teamName !== piece.teamName) {
      team = { teamName: piece.teamName, persons: [], pieces: 0 };
      teams.push(team);
    }
    let person = team.persons.at(-1);
    if (!person || person.personId !== piece.personId) {
      person = { personId: piece.personId, personName: piece.personName, bracelet: piece.bracelet, pieces: [] };
      team.persons.push(person);
    }
    person.pieces.push(piece);
    team.pieces += 1;
  }
  const personCount = new Set(shown.map((piece) => piece.personId)).size;

  // The Excel file of the pieces shown (column filters included).
  async function handleDownload() {
    if (!festival) return;
    setIsDownloading(true);
    try {
      const blob = await exportAtelierOpenHandouts({
        festivalId: festival.id,
        day: day === ALL ? null : day,
        lineIds: shown.map((piece) => piece.lineId),
        locale,
      });
      saveExcel(blob, "atelier-openstaand", festival.name);
    } catch {
      toast.error(t("downloadFailed"));
    } finally {
      setIsDownloading(false);
    }
  }

  // After a return (or cancelled pick-up): close, show what's left, re-count stock.
  function finishReturn() {
    setReturnPerson(null);
    setWriteOffPerson(null);
    rows.reload();
    window.dispatchEvent(new Event(ATELIER_STOCK_CHANGED_EVENT));
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight underline">{t("title")}</h1>
          <p className="text-muted-foreground">{t("description")}</p>
        </div>
        <div className="flex flex-wrap items-end gap-3">
          <AtelierFestivalSelect festivals={festivals} festival={festival} />
          <div className="flex w-40 flex-col gap-2">
            <Label htmlFor="atelier-open-day">{t("dayLabel")}</Label>
            <SearchableSelect
              value={day}
              onValueChange={(value) => setDay(value ?? ALL)}
              id="atelier-open-day"
              className="w-full"
              renderValue={(value: string | null) => (value && value !== ALL ? formatDateNl(value) : t("allDays"))}
              options={[
                { value: ALL, label: t("allDays") },
                ...(festival?.days ?? []).map((item) => ({ value: item, label: formatDateNl(item) })),
              ]}
            />
          </div>
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
              {hasActions && (
                <TableHead className="sticky top-0 right-0 z-30 bg-background text-right font-bold underline">
                  {t("actions")}
                </TableHead>
              )}
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
              {hasActions && <TableHead className="sticky top-10 right-0 z-30 bg-background" />}
            </TableRow>
          </TableHeader>
          <TableBody>
            {shown.length === 0 && (
              <TableRow>
                <TableCell colSpan={columnCount} className="text-center text-muted-foreground">
                  {rows.isLoading ? t("loading") : pieces.length > 0 ? t("noMatch") : t("empty")}
                </TableCell>
              </TableRow>
            )}
            {teams.map((team) => (
              <Fragment key={team.teamName}>
                {/* Team row: name + how many persons and pieces are still out. */}
                <TableRow className="bg-muted/60 hover:bg-muted/60">
                  <TableCell colSpan={columnCount} className="font-bold">
                    {team.teamName}
                    <span className="ml-3 text-sm font-normal text-muted-foreground">
                      {t("totals", { persons: team.persons.length, pieces: team.pieces })}
                    </span>
                  </TableCell>
                </TableRow>
                {team.persons.map((person) => (
                  <Fragment key={person.personId}>
                    {/* Person row: who, with their bracelet number. */}
                    <TableRow className="group bg-muted/20">
                      <TableCell />
                      <TableCell className="font-medium">{person.personName}</TableCell>
                      <TableCell className="font-mono text-xs">{person.bracelet}</TableCell>
                      <TableCell colSpan={4} className="text-sm text-muted-foreground">
                        {t("piecesCount", { pieces: person.pieces.length })}
                      </TableCell>
                      {hasActions && (
                        <TableCell className="sticky right-0 z-10 bg-background text-right group-hover:bg-muted/50">
                          <div className="flex justify-end gap-2">
                            {canBook && (
                              <Button variant="outline" size="sm" onClick={() => setReturnPerson(person)}>
                                <PackageMinus className="size-4" />
                                {t("returnButton")}
                              </Button>
                            )}
                            {canWriteOff && (
                              <Button variant="outline" size="sm" onClick={() => setWriteOffPerson(person)}>
                                <PackageX className="size-4" />
                                {t("writeOffButton")}
                              </Button>
                            )}
                          </div>
                        </TableCell>
                      )}
                    </TableRow>
                    {/* One line per piece the person still has. */}
                    {person.pieces.map((piece) => (
                      <TableRow key={piece.key} className="group">
                        <TableCell colSpan={3} />
                        <TableCell>{formatDateNl(piece.day)}</TableCell>
                        <TableCell>{piece.article}</TableCell>
                        <TableCell>{piece.size}</TableCell>
                        <TableCell className="text-sm text-muted-foreground">{formatDateTimeNl(piece.since)}</TableCell>
                        {hasActions && <TableCell className="sticky right-0 z-10 bg-background group-hover:bg-muted/50" />}
                      </TableRow>
                    ))}
                  </Fragment>
                ))}
              </Fragment>
            ))}
          </TableBody>
          {shown.length > 0 && (
            <TableFooter>
              <TableRow>
                <TableCell colSpan={columnCount} className="font-bold">
                  {t("totals", { persons: personCount, pieces: shown.length })}
                  {active && (
                    <span className="ml-3 font-normal text-muted-foreground">
                      {t("filteredOf", { shown: shown.length, total: pieces.length })}
                    </span>
                  )}
                </TableCell>
              </TableRow>
            </TableFooter>
          )}
        </Table>
      </div>

      {writeOffPerson && (
        <WriteOffDialog
          personId={writeOffPerson.personId}
          personName={writeOffPerson.personName}
          pieces={writeOffPerson.pieces}
          onClose={() => setWriteOffPerson(null)}
          onDone={finishReturn}
        />
      )}

      {/* The desk's return form, for this one person. */}
      {returnPerson && (
        <Dialog open onOpenChange={(open) => !open && setReturnPerson(null)}>
          <DialogContent className="max-h-[85vh] overflow-y-auto sm:max-w-3xl">
            <DialogHeader>
              <DialogTitle>{t("returnTitle")}</DialogTitle>
            </DialogHeader>
            <ReturnForm
              canCancel={canCancel}
              initialPerson={{
                id: returnPerson.personId,
                name: returnPerson.personName,
                email: null,
                bracelet_number: returnPerson.bracelet,
              }}
              fixedPerson
              initialQuery=""
              scan={null}
              onDone={finishReturn}
            />
          </DialogContent>
        </Dialog>
      )}
    </div>
  );
}
