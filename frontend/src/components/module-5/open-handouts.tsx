"use client";

// Atelier's "Balie > Openstaand" screen: the pieces that were picked up and
// not brought back yet, grouped per team (ploeg), then per person (with
// bracelet number; no email column, for privacy — GDPR), then one line per piece with
// its festival day and since when. Filters: festival + day at the top (they
// decide what's loaded) and a text filter above every column (client-side).
// Writing off what never comes back stays manual (Stock > Afboeken).

import { Fragment, useMemo, useState } from "react";
import { useTranslations } from "next-intl";
import { listAtelierOpenHandouts } from "@/lib/api";
import { formatDateNl, formatDateTimeNl } from "@/lib/date-time";
import type { AtelierHandout, Season } from "@/lib/types";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableFooter, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { AtelierFestivalSelect, useAtelierFestival } from "@/components/module-5/atelier-festival-select";
import { AtelierSeasonSelect, useAtelierSeasonId } from "@/components/module-5/atelier-season-select";
import { FilterHeadCell, useColumnFilters } from "@/components/module-5/column-filters";
import { useKeyedLoad } from "@/components/module-4/use-keyed-load";

// The day filter's "every day" choice (Base UI's Select needs a non-empty value).
const ALL = "all";

// The table's columns, in order (each has a text filter above it).
const COLUMNS = ["team", "person", "bracelet", "day", "article", "size", "since"] as const;
type Column = (typeof COLUMNS)[number];

// One open piece, with the texts its columns show (and filter on).
interface PieceRow {
  key: string;
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
}

export function OpenHandouts({ seasons }: OpenHandoutsProps) {
  const t = useTranslations("atelier.open");
  const tFit = useTranslations("atelier.fits");
  const seasonId = useAtelierSeasonId(seasons);
  const { festivals, festival } = useAtelierFestival(seasonId);
  const [day, setDay] = useState<string>(ALL);
  const { filters, setFilter, matches, active } = useColumnFilters<Column>();

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
            <Select value={day} onValueChange={(value) => setDay(value ?? ALL)}>
              <SelectTrigger id="atelier-open-day" className="w-full">
                <SelectValue>{(value: string | null) => (value && value !== ALL ? formatDateNl(value) : t("allDays"))}</SelectValue>
              </SelectTrigger>
              <SelectContent>
                <SelectItem value={ALL}>{t("allDays")}</SelectItem>
                {(festival?.days ?? []).map((item) => (
                  <SelectItem key={item} value={item}>
                    {formatDateNl(item)}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <AtelierSeasonSelect seasons={seasons} seasonId={seasonId} />
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
                  {rows.isLoading ? t("loading") : pieces.length > 0 ? t("noMatch") : t("empty")}
                </TableCell>
              </TableRow>
            )}
            {teams.map((team) => (
              <Fragment key={team.teamName}>
                {/* Team row: name + how many persons and pieces are still out. */}
                <TableRow className="bg-muted/60 hover:bg-muted/60">
                  <TableCell colSpan={COLUMNS.length} className="font-bold">
                    {team.teamName}
                    <span className="ml-3 text-sm font-normal text-muted-foreground">
                      {t("totals", { persons: team.persons.length, pieces: team.pieces })}
                    </span>
                  </TableCell>
                </TableRow>
                {team.persons.map((person) => (
                  <Fragment key={person.personId}>
                    {/* Person row: who, with their bracelet number. */}
                    <TableRow className="bg-muted/20">
                      <TableCell />
                      <TableCell className="font-medium">{person.personName}</TableCell>
                      <TableCell className="font-mono text-xs">{person.bracelet}</TableCell>
                      <TableCell colSpan={4} className="text-sm text-muted-foreground">
                        {t("piecesCount", { pieces: person.pieces.length })}
                      </TableCell>
                    </TableRow>
                    {/* One line per piece the person still has. */}
                    {person.pieces.map((piece) => (
                      <TableRow key={piece.key}>
                        <TableCell colSpan={3} />
                        <TableCell>{formatDateNl(piece.day)}</TableCell>
                        <TableCell>{piece.article}</TableCell>
                        <TableCell>{piece.size}</TableCell>
                        <TableCell className="text-sm text-muted-foreground">{formatDateTimeNl(piece.since)}</TableCell>
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
                <TableCell colSpan={COLUMNS.length} className="font-bold">
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
    </div>
  );
}
