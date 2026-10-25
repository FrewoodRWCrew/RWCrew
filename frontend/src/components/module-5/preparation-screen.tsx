"use client";

// Atelier's "Reservaties > Voorbereiden" screen: what the store has to
// prepare for a festival. Clothing comes back every evening and every team
// works each festival day, so every day needs the same: the store totals
// per article (with sizes estimated from the article's size split) and one
// bundle per team (persons × package; sizes are picked at the desk). The
// picklist PDF is printed per day, for every team or only the ticked ones.
// Next to each estimated size the available stock; a size the atelier
// doesn't own enough of is red, one that is still in the wash orange.

import { useState } from "react";
import { Printer } from "lucide-react";
import { useLocale, useTranslations } from "next-intl";
import { atelierPicklistUrl, getAtelierPreparation } from "@/lib/api";
import { formatDateNl } from "@/lib/date-time";
import type { AtelierPreparation, Season } from "@/lib/types";
import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { AtelierFestivalSelect, useAtelierFestival } from "@/components/module-5/atelier-festival-select";
import { AtelierSeasonSelect, useAtelierSeasonId } from "@/components/module-5/atelier-season-select";
import { useKeyedLoad } from "@/components/module-4/use-keyed-load";

interface PreparationScreenProps {
  seasons: Season[];
}

export function PreparationScreen({ seasons }: PreparationScreenProps) {
  const t = useTranslations("atelier.preparation");
  const tFit = useTranslations("atelier.fits");
  const locale = useLocale();
  const seasonId = useAtelierSeasonId(seasons);
  const { festivals, festival, isLoading: festivalsLoading } = useAtelierFestival(seasonId);

  const preparation = useKeyedLoad<AtelierPreparation>(festival ? String(festival.id) : null, () =>
    getAtelierPreparation(festival!.id),
  );
  const data = preparation.data;

  // The chosen day (for the picklist) and the ticked teams, kept per festival.
  const [chosen, setChosen] = useState<{ festivalId: number; day: string | null; teamIds: number[] } | null>(null);
  const current = chosen !== null && chosen.festivalId === festival?.id ? chosen : null;
  const day = current?.day ?? festival?.days[0] ?? null;
  const tickedTeamIds = current?.teamIds ?? [];

  function update(change: { day?: string; teamIds?: number[] }) {
    if (!festival) return;
    setChosen({ festivalId: festival.id, day, teamIds: tickedTeamIds, ...change });
  }

  function toggleTeam(teamId: number, checked: boolean) {
    update({ teamIds: checked ? [...tickedTeamIds, teamId] : tickedTeamIds.filter((id) => id !== teamId) });
  }

  // Ticked teams print only those; none ticked prints every team.
  function printPicklist() {
    if (!festival || !day) return;
    window.open(atelierPicklistUrl(festival.id, day, tickedTeamIds.length ? tickedTeamIds : null, locale), "_blank");
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight underline">{t("title")}</h1>
          <p className="text-muted-foreground">{t("description")}</p>
        </div>
        <div className="flex items-end gap-3">
          <AtelierFestivalSelect festivals={festivals} festival={festival} />
          <AtelierSeasonSelect seasons={seasons} seasonId={seasonId} />
        </div>
      </div>

      {!festivalsLoading && festival === null && <p className="text-sm text-muted-foreground">{t("noFestival")}</p>}
      {preparation.isLoading && <p className="text-sm text-muted-foreground">{t("loading")}</p>}
      {preparation.failed && <p className="text-sm text-destructive">{t("loadFailed")}</p>}

      {festival && data && (
        <>
          {/* The festival days (the same need each day) and the picklist button. */}
          <Card>
            <CardContent className="flex flex-wrap items-center justify-between gap-4">
              <div className="flex flex-col gap-2">
                <p className="text-sm text-muted-foreground">
                  {t("perDay", { persons: data.persons_per_day, pieces: data.pieces_per_day })}
                </p>
                <div className="flex flex-wrap gap-2">
                  {festival.days.map((item) => (
                    <button
                      key={item}
                      type="button"
                      onClick={() => update({ day: item })}
                      className={cn(
                        "rounded-full border px-3 py-1 text-sm",
                        item === day ? "border-primary bg-primary text-primary-foreground" : "hover:bg-muted",
                      )}
                    >
                      {formatDateNl(item)}
                    </button>
                  ))}
                </div>
              </div>
              <Button onClick={printPicklist} disabled={!day || data.bundles.length === 0}>
                <Printer className="size-4" />
                {tickedTeamIds.length
                  ? t("printTicked", { count: tickedTeamIds.length })
                  : t("printAll")}
              </Button>
            </CardContent>
          </Card>

          {data.teams_without_package.length > 0 && (
            <p className="text-sm text-destructive">
              {t("teamsWithoutPackage", { teams: data.teams_without_package.join(", ") })}
            </p>
          )}

          {/* Store totals per article, with the estimated sizes. */}
          <section className="flex flex-col gap-2">
            <h2 className="text-lg font-semibold">{t("totalsTitle")}</h2>
            <div className="rounded-md border [&>div]:max-h-[50vh] [&>div]:overflow-y-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="sticky top-0 z-20 bg-background font-bold underline">
                      {t("columnArticle")}
                    </TableHead>
                    <TableHead className="sticky top-0 z-20 w-24 bg-background text-right font-bold underline">
                      {t("columnTotal")}
                    </TableHead>
                    <TableHead className="sticky top-0 z-20 bg-background font-bold underline">
                      {t("columnSizes")}
                    </TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {data.articles.length === 0 && (
                    <TableRow>
                      <TableCell colSpan={3} className="text-center text-muted-foreground">
                        {t("nothing")}
                      </TableCell>
                    </TableRow>
                  )}
                  {data.articles.map((article) => (
                    <TableRow key={article.article_id}>
                      <TableCell>
                        <span className="font-medium">{article.article_name}</span>{" "}
                        <span className="font-mono text-xs text-muted-foreground">{article.article_code}</span>
                      </TableCell>
                      <TableCell className="text-right font-bold">{article.quantity}</TableCell>
                      <TableCell>
                        <div className="flex flex-wrap items-center gap-1.5">
                          {article.sizes
                            .filter((size) => size.quantity > 0)
                            .map((size) => (
                              // Red: the atelier doesn't own enough; orange: enough, but not all washed/back yet.
                              <Badge
                                key={size.size_id}
                                variant="outline"
                                title={t("stockTitle", { available: size.available, owned: size.owned })}
                                className={cn(
                                  size.quantity > size.owned &&
                                    "border-red-300 bg-red-50 text-red-800 dark:border-red-500/40 dark:bg-red-500/10 dark:text-red-200",
                                  size.quantity <= size.owned &&
                                    size.quantity > size.available &&
                                    "border-orange-300 bg-orange-50 text-orange-800 dark:border-orange-500/40 dark:bg-orange-500/10 dark:text-orange-200",
                                )}
                              >
                                {size.size_name} · {tFit(size.fit)}: {size.quantity}
                                <span className="ml-1 text-muted-foreground">({t("inStock", { count: size.available })})</span>
                              </Badge>
                            ))}
                          {article.equal_split && article.sizes.length > 0 && (
                            <span className="text-xs text-muted-foreground">{t("equalSplit")}</span>
                          )}
                        </div>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          </section>

          {/* One bundle per team; tick teams to print only their picklist. */}
          <section className="flex flex-col gap-2">
            <h2 className="text-lg font-semibold">{t("bundlesTitle")}</h2>
            {data.bundles.length === 0 && <p className="text-sm text-muted-foreground">{t("nothing")}</p>}
            <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-3">
              {data.bundles.map((bundle) => (
                <Card key={bundle.team_id}>
                  <CardContent className="flex flex-col gap-2">
                    <div className="flex items-center gap-2">
                      <Checkbox
                        id={`atelier-bundle-${bundle.team_id}`}
                        checked={tickedTeamIds.includes(bundle.team_id)}
                        onCheckedChange={(checked) => toggleTeam(bundle.team_id, checked === true)}
                      />
                      <label htmlFor={`atelier-bundle-${bundle.team_id}`} className="font-medium">
                        {bundle.team_name}
                      </label>
                      <Badge variant="secondary" className="ml-auto">
                        {t("persons", { count: bundle.persons })}
                      </Badge>
                    </div>
                    <ul className="text-sm text-muted-foreground">
                      {bundle.lines.map((line) => (
                        <li key={line.article_id}>
                          {line.quantity} × {line.article_name}
                        </li>
                      ))}
                    </ul>
                  </CardContent>
                </Card>
              ))}
            </div>
          </section>
        </>
      )}
    </div>
  );
}
