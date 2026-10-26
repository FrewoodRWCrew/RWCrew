"use client";

// Atelier's "Reservaties > Reservaties" screen: everything per festival on
// one page — per ploeg how many people need clothing and what each of them
// gets (the package: articles × pieces per person; the size is picked at the
// desk). The team works every festival day with that number and returns the
// clothing every evening. Every active team is listed; persons, notes and
// packages (edited in a dialog per team) are saved together with one Save.
// Above the table: last year's reservations of the same festival, to copy.
// Per ploeg "Festivals ingevuld" = how many of the festivals it picked in
// Altsien Select have persons filled in here; a text filter above every column.

import { useState } from "react";
import { Check, Copy, Package, Plus, Trash2, X } from "lucide-react";
import { useTranslations } from "next-intl";
import { toast } from "sonner";
import {
  ApiError,
  copyAtelierPreviousReservations,
  getAtelierPreviousReservations,
  listAtelierReservations,
  saveAtelierReservations,
} from "@/lib/api";
import { formatDateTimeNl } from "@/lib/date-time";
import type {
  AtelierArticle,
  AtelierPackageLine,
  AtelierPreviousReservations,
  AtelierReservationRow,
  Season,
} from "@/lib/types";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableFooter, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";
import { ArticleThumb } from "@/components/module-5/article-management";
import { AtelierFestivalSelect, useAtelierFestival } from "@/components/module-5/atelier-festival-select";
import { AtelierSeasonSelect, useAtelierSeasonId } from "@/components/module-5/atelier-season-select";
import { FilterHeadCell, useColumnFilters } from "@/components/module-5/column-filters";
import { useKeyedLoad } from "@/components/module-4/use-keyed-load";

/** One team's values as edited on screen. */
interface Draft {
  persons: number;
  note: string;
  lines: AtelierPackageLine[];
}

/** Whether two packages are the same (order doesn't matter). */
function sameLines(a: AtelierPackageLine[], b: AtelierPackageLine[]) {
  const key = (lines: AtelierPackageLine[]) =>
    lines
      .map((line) => `${line.article_id}:${line.quantity_per_person}`)
      .sort()
      .join(",");
  return key(a) === key(b);
}

// The columns with a text filter above them (Actions has none).
const FILTER_COLUMNS = ["team", "progress", "persons", "package", "note", "changed"] as const;
type FilterColumn = (typeof FILTER_COLUMNS)[number];

interface ReservationScreenProps {
  seasons: Season[];
  articles: AtelierArticle[];
  canEdit: boolean;
}

export function ReservationScreen({ seasons, articles, canEdit }: ReservationScreenProps) {
  const t = useTranslations("atelier.reservations");
  const seasonId = useAtelierSeasonId(seasons);
  const { festivals, festival, isLoading: festivalsLoading } = useAtelierFestival(seasonId);
  const festivalKey = festival ? String(festival.id) : null;

  const rows = useKeyedLoad<AtelierReservationRow[]>(festivalKey, () => listAtelierReservations(festival!.id));
  const previous = useKeyedLoad<AtelierPreviousReservations>(festivalKey, () =>
    getAtelierPreviousReservations(festival!.id),
  );
  // The edits not saved yet, per team — only kept for the festival they were made on.
  const [edits, setEdits] = useState<{ festivalId: number; byTeam: Record<number, Draft> } | null>(null);
  const [isSaving, setIsSaving] = useState(false);
  const { filters, setFilter, matches, active: filtering } = useColumnFilters<FilterColumn>();

  const articlesById = new Map(articles.map((article) => [article.id, article]));
  const pending = edits !== null && edits.festivalId === festival?.id ? edits.byTeam : {};
  const isDirty = Object.keys(pending).length > 0;

  // The value shown for a team: its edit, else what's saved.
  function valueOf(row: AtelierReservationRow): Draft {
    return pending[row.team_id] ?? { persons: row.persons, note: row.note ?? "", lines: row.lines };
  }

  function edit(row: AtelierReservationRow, change: Partial<Draft>) {
    if (!festival) return;
    const next = { ...valueOf(row), ...change };
    const byTeam = { ...pending };
    // Back to the saved values = no longer an edit.
    if (next.persons === row.persons && next.note.trim() === (row.note ?? "") && sameLines(next.lines, row.lines)) {
      delete byTeam[row.team_id];
    } else {
      byTeam[row.team_id] = next;
    }
    setEdits({ festivalId: festival.id, byTeam });
  }

  // A team's Altsien Select festivals with their "filled in" state; the
  // festival on screen follows the persons typed in (even before saving).
  function progressOf(row: AtelierReservationRow) {
    const picked = row.festivals_picked.map((item) =>
      item.festival_id === festival?.id ? { ...item, done: valueOf(row).persons > 0 } : item,
    );
    return { picked, done: picked.filter((item) => item.done).length };
  }

  // The rows matching every column filter; rows with unsaved edits always stay visible.
  const allRows = rows.data ?? [];
  const shownRows = allRows.filter((row) => {
    if (pending[row.team_id] !== undefined) return true;
    const value = valueOf(row);
    const progress = progressOf(row);
    return matches({
      team: row.team_name,
      progress: progress.picked.length === 0 ? t("noSelection") : `${progress.done}/${progress.picked.length}`,
      persons: value.persons,
      package: value.lines.map((line) => articlesById.get(line.article_id)?.name ?? "").join(" "),
      note: value.note,
      changed: row.updated_at ? `${formatDateTimeNl(row.updated_at)} ${row.updated_by_name ?? ""}` : "",
    });
  });

  // Persons per festival day, including the edits not saved yet.
  const totalPersons = (rows.data ?? []).reduce((sum, row) => sum + valueOf(row).persons, 0);
  const dayCount = festival?.days.length ?? 0;

  async function handleSave() {
    if (!festival) return;
    setIsSaving(true);
    try {
      const saved = await saveAtelierReservations(
        festival.id,
        Object.entries(pending).map(([teamId, draft]) => ({
          team_id: Number(teamId),
          persons: draft.persons,
          note: draft.note.trim() || null,
          lines: draft.lines,
        })),
      );
      rows.setData(saved);
      setEdits(null);
      toast.success(t("saved"));
    } catch (error) {
      toast.error(error instanceof ApiError ? error.message : t("saveFailed"));
    } finally {
      setIsSaving(false);
    }
  }

  async function handleCopy(teamIds: number[]) {
    if (!festival || teamIds.length === 0) return;
    if (isDirty && !window.confirm(t("discardChanges"))) return;
    try {
      const result = await copyAtelierPreviousReservations(festival.id, teamIds);
      toast.success(t("copied", { count: result.teams_changed }));
      if (result.skipped_inactive > 0) {
        toast.warning(t("copySkippedInactive", { count: result.skipped_inactive }));
      }
      setEdits(null);
      rows.reload();
    } catch (error) {
      toast.error(error instanceof ApiError ? error.message : t("copyFailed"));
    }
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
          <AtelierSeasonSelect seasons={seasons} seasonId={seasonId} />
        </div>
      </div>

      {!festivalsLoading && festival === null ? (
        <p className="text-sm text-muted-foreground">{t("noFestival")}</p>
      ) : (
        <>
          {canEdit && previous.data?.festival && previous.data.rows.length > 0 && (
            <CopyFromLastYear previous={previous.data} articlesById={articlesById} onCopy={handleCopy} />
          )}

          <TooltipProvider delay={200}>
          <div className="rounded-md border [&>div]:max-h-[65vh] [&>div]:overflow-y-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="sticky top-0 z-20 bg-background font-bold underline">{t("columnTeam")}</TableHead>
                  <TableHead className="sticky top-0 z-20 bg-background font-bold underline">{t("columnProgress")}</TableHead>
                  <TableHead className="sticky top-0 z-20 w-28 bg-background font-bold underline">
                    {t("columnPersons")}
                  </TableHead>
                  <TableHead className="sticky top-0 z-20 bg-background font-bold underline">
                    {t("columnPackage")}
                  </TableHead>
                  <TableHead className="sticky top-0 z-20 bg-background font-bold underline">{t("columnNote")}</TableHead>
                  <TableHead className="sticky top-0 z-20 bg-background font-bold underline">
                    {t("columnChanged")}
                  </TableHead>
                  <TableHead className="sticky top-0 right-0 z-30 bg-background text-right font-bold underline">
                    {t("tableActions")}
                  </TableHead>
                </TableRow>
                {/* One text filter above every column (the Actions corner stays empty). */}
                <TableRow>
                  {FILTER_COLUMNS.map((column) => (
                    <FilterHeadCell
                      key={column}
                      label={t("filter", { column: t(`filterColumns.${column}`) })}
                      value={filters[column]}
                      onChange={(value) => setFilter(column, value)}
                    />
                  ))}
                  <TableHead className="sticky top-10 right-0 z-30 bg-background" />
                </TableRow>
              </TableHeader>
              <TableBody>
                {rows.isLoading && (
                  <TableRow>
                    <TableCell colSpan={7} className="text-center text-muted-foreground">
                      {t("loading")}
                    </TableCell>
                  </TableRow>
                )}
                {!rows.isLoading && shownRows.length === 0 && (
                  <TableRow>
                    <TableCell colSpan={7} className="text-center text-muted-foreground">
                      {allRows.length === 0 ? t("noTeams") : t("noMatch")}
                    </TableCell>
                  </TableRow>
                )}
                {shownRows.map((row) => {
                  const value = valueOf(row);
                  const changed = pending[row.team_id] !== undefined;
                  const progress = progressOf(row);
                  // The team picked festivals in Altsien Select, but not this one.
                  const notPicked =
                    progress.picked.length > 0 && !progress.picked.some((item) => item.festival_id === festival?.id);
                  return (
                    <TableRow
                      key={row.team_id}
                      className={changed ? "group bg-amber-50 dark:bg-amber-500/10" : "group"}
                    >
                      <TableCell className="font-medium">
                        <span className={row.team_active ? undefined : "italic"}>{row.team_name}</span>
                        {notPicked && (
                          <Badge variant="outline" className="ml-2 font-normal text-muted-foreground">
                            {t("notPicked")}
                          </Badge>
                        )}
                      </TableCell>
                      <TableCell>
                        {progress.picked.length === 0 ? (
                          <span className="text-sm text-muted-foreground italic">{t("noSelection")}</span>
                        ) : (
                          // Green when every picked festival is filled in, orange otherwise;
                          // the tooltip lists the festivals with a tick or a cross.
                          <Tooltip>
                            <TooltipTrigger
                              render={
                                <span
                                  className={
                                    progress.done === progress.picked.length
                                      ? "rounded bg-emerald-100 px-2 py-0.5 font-medium text-emerald-800 dark:bg-emerald-500/20 dark:text-emerald-300"
                                      : "rounded bg-amber-100 px-2 py-0.5 font-medium text-amber-800 dark:bg-amber-500/20 dark:text-amber-300"
                                  }
                                />
                              }
                            >
                              {t("progress", { done: progress.done, total: progress.picked.length })}
                            </TooltipTrigger>
                            <TooltipContent className="text-sm">
                              <ul className="flex flex-col gap-1">
                                {progress.picked.map((item) => (
                                  <li key={item.festival_id} className="flex items-center gap-1.5">
                                    {item.done ? <Check className="size-4" /> : <X className="size-4" />}
                                    {item.name}
                                  </li>
                                ))}
                              </ul>
                            </TooltipContent>
                          </Tooltip>
                        )}
                      </TableCell>
                      <TableCell>
                        {canEdit ? (
                          <Input
                            type="number"
                            min={0}
                            max={9999}
                            step={1}
                            className="w-24"
                            aria-label={t("personsFor", { team: row.team_name })}
                            value={value.persons}
                            onChange={(event) =>
                              edit(row, {
                                persons: Math.min(9999, Math.max(0, Number.parseInt(event.target.value, 10) || 0)),
                              })
                            }
                          />
                        ) : (
                          value.persons
                        )}
                      </TableCell>
                      <TableCell className="max-w-md whitespace-normal">
                        <PackageSummary lines={value.lines} articlesById={articlesById} />
                        {value.persons > 0 && value.lines.length === 0 && (
                          <Badge variant="destructive">{t("noPackage")}</Badge>
                        )}
                      </TableCell>
                      <TableCell>
                        {canEdit ? (
                          <Input
                            aria-label={t("noteFor", { team: row.team_name })}
                            value={value.note}
                            onChange={(event) => edit(row, { note: event.target.value })}
                          />
                        ) : (
                          <span className="text-sm">{row.note}</span>
                        )}
                      </TableCell>
                      <TableCell className="text-xs text-muted-foreground">
                        {row.updated_at && `${formatDateTimeNl(row.updated_at)} · ${row.updated_by_name ?? ""}`}
                      </TableCell>
                      <TableCell
                        className={
                          changed
                            ? "sticky right-0 z-10 bg-amber-50 dark:bg-amber-950"
                            : "sticky right-0 z-10 bg-background group-hover:bg-muted/50"
                        }
                      >
                        <div className="flex justify-end">
                          <PackageDialog
                            teamName={row.team_name}
                            lines={value.lines}
                            articles={articles}
                            canEdit={canEdit}
                            onApply={(lines) => edit(row, { lines })}
                          />
                        </div>
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
              <TableFooter>
                <TableRow>
                  <TableCell colSpan={2} className="font-bold">
                    {t("totalPerDay", { days: dayCount })}
                    {/* The totals always count every team, also the ones hidden by a filter. */}
                    {filtering && (
                      <span className="ml-3 font-normal text-muted-foreground">
                        {t("filteredOf", { shown: shownRows.length, total: allRows.length })}
                      </span>
                    )}
                  </TableCell>
                  <TableCell className="font-bold">{totalPersons}</TableCell>
                  <TableCell colSpan={4} />
                </TableRow>
              </TableFooter>
            </Table>
          </div>
          </TooltipProvider>

          {canEdit && (
            <div className="flex items-center justify-end gap-3">
              {isDirty && <span className="text-sm text-muted-foreground">{t("unsaved")}</span>}
              <Button onClick={handleSave} disabled={isSaving || !isDirty}>
                {t("save")}
              </Button>
            </div>
          )}
        </>
      )}
    </div>
  );
}

/** A package as small chips, e.g. "2 × T-shirt". */
function PackageSummary({
  lines,
  articlesById,
}: {
  lines: AtelierPackageLine[];
  articlesById: Map<number, AtelierArticle>;
}) {
  if (lines.length === 0) return null;
  return (
    <div className="mb-1 flex flex-wrap gap-1">
      {lines.map((line) => (
        <Badge key={line.article_id} variant="outline">
          {line.quantity_per_person} × {articlesById.get(line.article_id)?.name ?? "?"}
        </Badge>
      ))}
    </div>
  );
}

interface PackageDialogProps {
  teamName: string;
  lines: AtelierPackageLine[];
  articles: AtelierArticle[];
  canEdit: boolean;
  /** Puts the edited package into the screen's draft (saved with Save). */
  onApply: (lines: AtelierPackageLine[]) => void;
}

/** One team's package for this festival: add articles, change the pieces per person, remove lines. */
function PackageDialog({ teamName, lines, articles, canEdit, onApply }: PackageDialogProps) {
  const t = useTranslations("atelier.reservations");
  const [isOpen, setIsOpen] = useState(false);
  const [draft, setDraft] = useState<AtelierPackageLine[]>(lines);
  const articlesById = new Map(articles.map((article) => [article.id, article]));

  function handleOpenChange(open: boolean) {
    setIsOpen(open);
    // Start from the team's current package every time the dialog opens.
    if (open) setDraft(lines);
  }

  // Articles that can still be added: active and not in the package yet.
  const addable = articles.filter((article) => article.active && !draft.some((line) => line.article_id === article.id));

  return (
    <Dialog open={isOpen} onOpenChange={handleOpenChange}>
      <DialogTrigger
        render={
          <Button variant="ghost" size="sm" title={t("editPackage")}>
            <Package className="size-4" />
            {t("packageButton")}
          </Button>
        }
      />
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>{t("packageTitle", { team: teamName })}</DialogTitle>
          <DialogDescription>{t("packageDescription")}</DialogDescription>
        </DialogHeader>

        <div className="flex flex-col gap-2">
          {draft.length === 0 && <p className="text-sm text-muted-foreground">{t("emptyPackage")}</p>}
          {draft.map((line) => {
            const article = articlesById.get(line.article_id);
            return (
              <div key={line.article_id} className="flex items-center gap-3">
                {article && <ArticleThumb article={article} />}
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-medium">{article?.name}</p>
                  <p className="font-mono text-xs text-muted-foreground">
                    {article?.code}
                    {article && !article.active && ` · ${t("inactive")}`}
                  </p>
                </div>
                {canEdit ? (
                  <>
                    {/* Always 1: at the desk every package article is one piece per person. */}
                    <Input
                      type="number"
                      className="w-20"
                      aria-label={t("quantityFor", { article: article?.name ?? "" })}
                      title={t("quantityFixed")}
                      value={1}
                      readOnly
                      disabled
                    />
                    <Button
                      variant="ghost"
                      size="icon"
                      aria-label={t("removeLine")}
                      title={t("removeLine")}
                      onClick={() => setDraft(draft.filter((item) => item.article_id !== line.article_id))}
                    >
                      <Trash2 className="size-4 text-destructive" />
                    </Button>
                  </>
                ) : (
                  <span className="text-sm">× {line.quantity_per_person}</span>
                )}
              </div>
            );
          })}

          {canEdit && (
            // Picking an article adds it with 1 piece per person.
            <Select
              value=""
              onValueChange={(value) => value && setDraft([...draft, { article_id: Number(value), quantity_per_person: 1 }])}
              disabled={addable.length === 0}
            >
              <SelectTrigger className="w-full">
                <Plus className="size-4" />
                <SelectValue>{() => t("addArticle")}</SelectValue>
              </SelectTrigger>
              <SelectContent>
                {addable.map((article) => (
                  <SelectItem key={article.id} value={String(article.id)}>
                    {article.name} ({article.code})
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          )}
        </div>

        {canEdit && (
          <DialogFooter>
            <Button
              onClick={() => {
                onApply(draft);
                setIsOpen(false);
              }}
            >
              {t("applyPackage")}
            </Button>
          </DialogFooter>
        )}
      </DialogContent>
    </Dialog>
  );
}

interface CopyFromLastYearProps {
  previous: AtelierPreviousReservations;
  articlesById: Map<number, AtelierArticle>;
  onCopy: (teamIds: number[]) => void;
}

/** Last year's reservations of the same festival, with a checkbox per team and a Copy button. */
function CopyFromLastYear({ previous, articlesById, onCopy }: CopyFromLastYearProps) {
  const t = useTranslations("atelier.reservations");
  const [ticked, setTicked] = useState<number[]>([]);
  const allTicked = ticked.length === previous.rows.length;

  function toggle(teamId: number, checked: boolean) {
    setTicked(checked ? [...ticked, teamId] : ticked.filter((id) => id !== teamId));
  }

  return (
    <Card>
      <CardContent className="flex flex-col gap-3">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <p className="font-medium">{t("previousTitle", { festival: previous.festival?.name ?? "" })}</p>
            <p className="text-sm text-muted-foreground">{t("previousHelp")}</p>
          </div>
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-2">
              <Checkbox
                id="atelier-copy-all"
                checked={allTicked}
                onCheckedChange={(checked) => setTicked(checked === true ? previous.rows.map((row) => row.team_id) : [])}
              />
              <label htmlFor="atelier-copy-all" className="text-sm">
                {t("selectAll")}
              </label>
            </div>
            <Button
              variant="outline"
              disabled={ticked.length === 0}
              onClick={() => {
                onCopy(ticked);
                setTicked([]);
              }}
            >
              <Copy className="size-4" />
              {t("copy", { count: ticked.length })}
            </Button>
          </div>
        </div>
        <div className="grid max-h-48 grid-cols-1 gap-x-6 gap-y-1 overflow-y-auto md:grid-cols-2">
          {previous.rows.map((row) => (
            <div key={row.team_id} className="flex items-start gap-2 text-sm">
              <Checkbox
                id={`atelier-copy-${row.team_id}`}
                checked={ticked.includes(row.team_id)}
                onCheckedChange={(checked) => toggle(row.team_id, checked === true)}
              />
              <label htmlFor={`atelier-copy-${row.team_id}`}>
                <span className="font-medium">{row.team_name}</span>
                <span className="text-muted-foreground">
                  {" · "}
                  {t("personsShort", { count: row.persons })}
                  {row.lines.length > 0 &&
                    ` · ${row.lines
                      .map((line) => `${line.quantity_per_person} × ${articlesById.get(line.article_id)?.name ?? "?"}`)
                      .join(", ")}`}
                </span>
              </label>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
