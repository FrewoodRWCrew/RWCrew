"use client";

// Altsien Select's "Ploegfiche": pick a team (and season), and see everything
// chosen for it in the Ploeg Wizard on one screen — team info, the progress
// of every wizard step, the festivals with their delivery locations, the
// products and walkie-talkies (placeholders until those modules exist) and
// the special requests with their status and the organisation's answer.
// The "PDF" button opens the same overview as a printable PDF with the
// Altsien logo (built by the backend, module_8/ploegfiche_pdf.py).

import { Check, Circle, FileDown, Pencil } from "lucide-react";
import { useLocale, useTranslations } from "next-intl";
import { useSearchParams } from "next/navigation";
import { Link, usePathname, useRouter } from "@/i18n/navigation";
import { altsienSelectPloegfichePdfUrl, getAltsienSelectPloegfiche, listAltsienSelectTeams } from "@/lib/api";
import type { AltsienSelectTeamState, AltsienSelectTeamSummary, Season } from "@/lib/types";
import { buttonVariants } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { AltsienSeasonSelect, useAltsienSeasonId } from "@/components/module-8/altsien-season-select";
import { RequestStatusBadge } from "@/components/module-8/request-status-badge";
import { useKeyedLoad } from "@/components/module-8/use-keyed-load";
import { formatDate, formatFestivalPeriod } from "@/components/module-8/wizard/format";
import { useStepText } from "@/components/module-8/wizard/use-step-text";

interface PloegficheProps {
  seasons: Season[];
  canOpenWizard: boolean;
}

export function Ploegfiche({ seasons, canOpenWizard }: PloegficheProps) {
  const t = useTranslations("altsienSelect.ploegfiche");
  const locale = useLocale();
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const seasonId = useAltsienSeasonId(seasons);
  const teamId = Number(searchParams.get("team")) || null;

  // The teams to choose from, and the chosen team's full overview.
  const teams = useKeyedLoad<AltsienSelectTeamSummary[]>(seasonId === null ? null : String(seasonId), () =>
    listAltsienSelectTeams(seasonId as number),
  );
  const fiche = useKeyedLoad<AltsienSelectTeamState>(
    seasonId !== null && teamId !== null ? `${seasonId}:${teamId}` : null,
    () => getAltsienSelectPloegfiche(teamId as number, seasonId as number),
  );

  // The chosen team lives in the URL (?team=), next to ?season=.
  function selectTeam(value: string | null) {
    const params = new URLSearchParams(searchParams.toString());
    if (value) params.set("team", value);
    else params.delete("team");
    if (seasonId !== null) params.set("season", String(seasonId));
    router.replace(`${pathname}?${params.toString()}`);
  }

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight underline">{t("title")}</h1>
          <p className="text-muted-foreground">{t("description")}</p>
        </div>
        <AltsienSeasonSelect seasons={seasons} seasonId={seasonId} />
      </div>

      <div className="flex flex-wrap items-end gap-3">
        <div className="flex w-full max-w-sm flex-col gap-2">
          <Label htmlFor="ploegfiche-team">{t("teamLabel")}</Label>
          <Select value={teamId !== null ? String(teamId) : ""} onValueChange={selectTeam}>
            <SelectTrigger id="ploegfiche-team">
              <SelectValue>
                {(value: string | null) =>
                  teams.data?.find((team) => String(team.team_id) === value)?.team_name ?? t("teamPlaceholder")
                }
              </SelectValue>
            </SelectTrigger>
            <SelectContent>
              {(teams.data ?? []).map((team) => (
                <SelectItem key={team.team_id} value={String(team.team_id)}>
                  {team.team_name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        {fiche.data && seasonId !== null && teamId !== null && (
          <>
            {/* A plain link: the browser sends the auth cookies along and shows the PDF in a new tab. */}
            <a
              href={altsienSelectPloegfichePdfUrl(teamId, seasonId, locale)}
              target="_blank"
              rel="noopener noreferrer"
              className={buttonVariants()}
            >
              <FileDown className="size-4" />
              {t("pdf")}
            </a>
            {canOpenWizard && (
              <Link
                href={`/modules/module-8/ploeg-wizard/${teamId}?season=${seasonId}`}
                className={buttonVariants({ variant: "outline" })}
              >
                <Pencil className="size-4" />
                {t("openWizard")}
              </Link>
            )}
          </>
        )}
      </div>

      {seasonId === null && <p className="text-sm text-muted-foreground">{t("noSeason")}</p>}
      {teams.data && teams.data.length === 0 && <p className="text-sm text-muted-foreground">{t("noTeams")}</p>}
      {teamId === null && teams.data && teams.data.length > 0 && (
        <p className="text-sm text-muted-foreground">{t("selectTeam")}</p>
      )}
      {fiche.isLoading && <p className="text-sm text-muted-foreground">{t("loading")}</p>}
      {fiche.failed && <p className="text-sm text-destructive">{t("loadError")}</p>}
      {fiche.data && <PloegficheContent state={fiche.data} />}
    </div>
  );
}

/** The overview itself, one card per section, in wizard order. */
function PloegficheContent({ state }: { state: AltsienSelectTeamState }) {
  const t = useTranslations("altsienSelect.ploegfiche");
  const stepText = useStepText();
  const doneByKey = new Map(state.progress.map((item) => [item.step_key, item]));
  const selectedFestivals = state.festivals.filter((festival) => festival.selected);

  // Each step's own section. A step without one (e.g. added later) only
  // appears in the progress card.
  const sections: Record<string, React.ReactNode> = {
    festivals: (
      <Card key="festivals">
        <CardHeader>
          <CardTitle>{t("festivalsTitle")}</CardTitle>
        </CardHeader>
        <CardContent>
          {selectedFestivals.length === 0 ? (
            <p className="text-sm text-muted-foreground">{t("noFestivals")}</p>
          ) : (
            <div className="rounded-md border [&>div]:max-h-[65vh] [&>div]:overflow-y-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="sticky top-0 z-20 bg-background font-bold underline">
                      {t("columnFestival")}
                    </TableHead>
                    <TableHead className="sticky top-0 z-20 bg-background font-bold underline">
                      {t("columnPeriod")}
                    </TableHead>
                    <TableHead className="sticky top-0 z-20 bg-background font-bold underline">
                      {t("columnAfleverlocatie")}
                    </TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {selectedFestivals.map((festival) => (
                    <TableRow key={festival.festival_id}>
                      <TableCell className="font-medium">{festival.festival_name}</TableCell>
                      <TableCell className="text-muted-foreground tabular-nums">
                        {formatFestivalPeriod(festival.start_date, festival.end_date)}
                      </TableCell>
                      <TableCell>
                        {festival.afleverlocatie_name ? (
                          <div className="flex flex-col">
                            <span>{festival.afleverlocatie_name}</span>
                            {festival.afleverlocatie_description && (
                              <span className="text-xs text-muted-foreground">
                                {festival.afleverlocatie_description}
                              </span>
                            )}
                          </div>
                        ) : (
                          <span className="text-muted-foreground italic">{t("noAfleverlocatie")}</span>
                        )}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}
        </CardContent>
      </Card>
    ),
    products: <PlaceholderCard key="products" title={stepText({ key: "products", label: "Products" }).title} />,
    special_requests: (
      <Card key="special_requests">
        <CardHeader>
          <CardTitle>{t("requestsTitle")}</CardTitle>
        </CardHeader>
        <CardContent>
          {state.requests.length === 0 ? (
            <p className="text-sm text-muted-foreground">{t("noRequests")}</p>
          ) : (
            <ul className="flex flex-col gap-2">
              {state.requests.map((request) => (
                <li key={request.id} className="flex flex-col gap-1.5 rounded-md border p-3">
                  <div className="flex items-start justify-between gap-3">
                    <p className="text-sm whitespace-pre-wrap">{request.text}</p>
                    <RequestStatusBadge name={request.status_name} color={request.status_color} />
                  </div>
                  <p className="text-xs text-muted-foreground">
                    {t("requestBy", { name: request.created_by_name ?? "—", date: formatDate(request.created_at) })}
                  </p>
                  {request.organisation_note && (
                    <p className="rounded bg-muted px-2 py-1 text-sm">
                      <span className="font-medium">{t("organisationNote")}:</span> {request.organisation_note}
                    </p>
                  )}
                </li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>
    ),
    walkies: <PlaceholderCard key="walkies" title={stepText({ key: "walkies", label: "Walkie-talkies" }).title} />,
  };

  return (
    <div className="flex flex-col gap-4">
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>{t("teamInfoTitle")}</CardTitle>
          </CardHeader>
          <CardContent>
            <dl className="grid grid-cols-[auto_1fr] gap-x-6 gap-y-2 text-sm">
              <dt className="font-medium text-muted-foreground">{t("team")}</dt>
              <dd>{state.team.name}</dd>
              <dt className="font-medium text-muted-foreground">{t("season")}</dt>
              <dd>
                {state.season_name}
                {!state.season_open && <span className="text-muted-foreground"> ({t("seasonClosed")})</span>}
              </dd>
              <dt className="font-medium text-muted-foreground">{t("location")}</dt>
              <dd>{state.team.location ?? "—"}</dd>
              <dt className="font-medium text-muted-foreground">{t("deliveryMethod")}</dt>
              <dd>{state.team.delivery_method ?? "—"}</dd>
              <dt className="font-medium text-muted-foreground">{t("kernleden")}</dt>
              <dd>{state.team.kernleden.length ? state.team.kernleden.join(", ") : "—"}</dd>
              {state.team.description && (
                <>
                  <dt className="font-medium text-muted-foreground">{t("teamDescription")}</dt>
                  <dd className="whitespace-pre-wrap">{state.team.description}</dd>
                </>
              )}
            </dl>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>{t("progressTitle")}</CardTitle>
          </CardHeader>
          <CardContent>
            <ul className="flex flex-col gap-2 text-sm">
              {state.steps.map((step) => {
                const done = doneByKey.get(step.key);
                return (
                  <li key={step.key} className="flex items-center gap-3">
                    {done ? (
                      <span className="flex size-5 items-center justify-center rounded-full bg-green-600 text-white">
                        <Check className="size-3.5" aria-hidden="true" />
                      </span>
                    ) : (
                      <Circle className="size-5 text-muted-foreground" aria-hidden="true" />
                    )}
                    <span className="w-40 font-medium">{stepText(step).title}</span>
                    <span className={done ? "text-green-700 dark:text-green-400" : "text-muted-foreground"}>
                      {done
                        ? t("stepDone", { date: formatDate(done.completed_at), name: done.completed_by_name ?? "—" })
                        : t("stepTodo")}
                    </span>
                  </li>
                );
              })}
            </ul>
          </CardContent>
        </Card>
      </div>

      {state.steps.map((step) => sections[step.key] ?? null)}
    </div>
  );
}

/** A section whose content will come from a module that doesn't exist yet. */
function PlaceholderCard({ title }: { title: string }) {
  const t = useTranslations("altsienSelect.ploegfiche");
  return (
    <Card>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
      </CardHeader>
      <CardContent>
        <p className="text-sm text-muted-foreground italic">{t("placeholder")}</p>
      </CardContent>
    </Card>
  );
}
