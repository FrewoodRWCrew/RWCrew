"use client";

// Atelier's "Balie > Openstaand" screen: the pieces that were picked up and
// not brought back yet — per person (with their bracelet number), with their email (to contact them),
// team, festival day and since when. Filters: festival (+ day) and team.
// Writing off what never comes back stays manual (Stock > Afboeken).

import { useState } from "react";
import { useTranslations } from "next-intl";
import { listAtelierDeskTeams, listAtelierOpenHandouts } from "@/lib/api";
import { formatDateNl, formatDateTimeNl } from "@/lib/date-time";
import type { AtelierDeskTeam, AtelierHandout, Season } from "@/lib/types";
import { Badge } from "@/components/ui/badge";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableFooter, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { AtelierFestivalSelect, useAtelierFestival } from "@/components/module-5/atelier-festival-select";
import { AtelierSeasonSelect, useAtelierSeasonId } from "@/components/module-5/atelier-season-select";
import { useKeyedLoad } from "@/components/module-4/use-keyed-load";

// The filters' "every day / every team" choice (Base UI's Select needs a non-empty value).
const ALL = "all";

interface OpenHandoutsProps {
  seasons: Season[];
}

export function OpenHandouts({ seasons }: OpenHandoutsProps) {
  const t = useTranslations("atelier.open");
  const tFit = useTranslations("atelier.fits");
  const seasonId = useAtelierSeasonId(seasons);
  const { festivals, festival } = useAtelierFestival(seasonId);
  const [day, setDay] = useState<string>(ALL);
  const [teamId, setTeamId] = useState<string>(ALL);

  const teams = useKeyedLoad<AtelierDeskTeam[]>(festival ? String(festival.id) : null, () => listAtelierDeskTeams(festival!.id));
  const key = festival ? `${festival.id}-${day}-${teamId}` : null;
  const rows = useKeyedLoad<AtelierHandout[]>(key, () =>
    listAtelierOpenHandouts({
      festivalId: festival!.id,
      day: day === ALL ? null : day,
      teamId: teamId === ALL ? null : Number(teamId),
    }),
  );
  const data = rows.data ?? [];
  const pieces = data.reduce((sum, row) => sum + row.lines.length, 0);

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
              <SelectTrigger id="atelier-open-day">
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
          <div className="flex w-48 flex-col gap-2">
            <Label htmlFor="atelier-open-team">{t("teamLabel")}</Label>
            <Select value={teamId} onValueChange={(value) => setTeamId(value ?? ALL)}>
              <SelectTrigger id="atelier-open-team">
                <SelectValue>
                  {(value: string | null) =>
                    value && value !== ALL
                      ? (teams.data?.find((team) => String(team.team_id) === value)?.team_name ?? "")
                      : t("allTeams")
                  }
                </SelectValue>
              </SelectTrigger>
              <SelectContent>
                <SelectItem value={ALL}>{t("allTeams")}</SelectItem>
                {(teams.data ?? []).map((team) => (
                  <SelectItem key={team.team_id} value={String(team.team_id)}>
                    {team.team_name}
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
              <TableHead className="sticky top-0 z-20 bg-background font-bold underline">{t("person")}</TableHead>
              <TableHead className="sticky top-0 z-20 bg-background font-bold underline">{t("email")}</TableHead>
              <TableHead className="sticky top-0 z-20 bg-background font-bold underline">{t("team")}</TableHead>
              <TableHead className="sticky top-0 z-20 bg-background font-bold underline">{t("day")}</TableHead>
              <TableHead className="sticky top-0 z-20 bg-background font-bold underline">{t("pieces")}</TableHead>
              <TableHead className="sticky top-0 z-20 bg-background font-bold underline">{t("since")}</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {data.length === 0 && (
              <TableRow>
                <TableCell colSpan={6} className="text-center text-muted-foreground">
                  {rows.isLoading ? t("loading") : t("empty")}
                </TableCell>
              </TableRow>
            )}
            {data.map((row) => (
              <TableRow key={row.id}>
                <TableCell>
                  <p className="font-medium">{row.person_name}</p>
                  {row.bracelet_number && (
                    <p className="font-mono text-xs text-muted-foreground">{row.bracelet_number}</p>
                  )}
                </TableCell>
                <TableCell>
                  {/* The email is optional. */}
                  {row.email && (
                    <a href={`mailto:${row.email}`} className="text-primary hover:underline">
                      {row.email}
                    </a>
                  )}
                </TableCell>
                <TableCell>{row.team_name}</TableCell>
                <TableCell>{formatDateNl(row.day)}</TableCell>
                <TableCell>
                  <div className="flex flex-wrap gap-1">
                    {row.lines.map((line) => (
                      <Badge key={line.id} variant="outline">
                        {line.article_name} · {line.size_name} · {tFit(line.fit)}
                      </Badge>
                    ))}
                  </div>
                </TableCell>
                <TableCell className="text-sm text-muted-foreground">{formatDateTimeNl(row.created_at)}</TableCell>
              </TableRow>
            ))}
          </TableBody>
          {data.length > 0 && (
            <TableFooter>
              <TableRow>
                <TableCell colSpan={6} className="font-bold">
                  {t("totals", { persons: new Set(data.map((row) => row.person_id)).size, pieces })}
                </TableCell>
              </TableRow>
            </TableFooter>
          )}
        </Table>
      </div>
    </div>
  );
}
