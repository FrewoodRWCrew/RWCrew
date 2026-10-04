"use client";

// MasterData's "Ploegverantwoordelijken" screen (nested under "Teams"):
// the people responsible for a team in a given season. They are plain
// contact records, not RWCrew users. Same dialog/table pattern as
// team-management.tsx, plus a Season/Team filter bar above the table.

import { useState } from "react";
import { Pencil, Trash2 } from "lucide-react";
import { useTranslations } from "next-intl";
import { toast } from "sonner";
import { useRouter } from "@/i18n/navigation";
import { useSelectedSeason } from "@/components/shared/season-provider";
import { ApiError, createTeamResponsible, deleteTeamResponsible, updateTeamResponsible } from "@/lib/api";
import type { TeamResponsible, TeamResponsibleInput } from "@/lib/types";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import { Button } from "@/components/ui/button";
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
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Textarea } from "@/components/ui/textarea";

interface NamedOption {
  id: number;
  name: string;
}

interface TeamResponsibleManagementProps {
  initialTeamResponsibles: TeamResponsible[];
  teams: NamedOption[];
  seasons: NamedOption[];
}

// Base UI's Select needs every item to have a non-empty value, so "all"
// in the filter bar is represented by this sentinel string instead of "".
const ALL_VALUE = "all";

// The form's own shape allows team/season to be null while the user
// hasn't picked one yet — TeamResponsibleInput itself keeps them required.
interface TeamResponsibleFormState extends Omit<TeamResponsibleInput, "team_id" | "season_id" | "comments"> {
  team_id: number | null;
  season_id: number | null;
  comments: string;
}

function toFormValues(teamResponsible: TeamResponsible): TeamResponsibleFormState {
  return {
    team_id: teamResponsible.team_id,
    season_id: teamResponsible.season_id,
    name: teamResponsible.name,
    email: teamResponsible.email,
    phone: teamResponsible.phone,
    comments: teamResponsible.comments ?? "",
  };
}

// Same order the backend returns: by team name, then person name.
function sortRows(rows: TeamResponsible[], teamNameFor: (teamId: number) => string) {
  return [...rows].sort(
    (a, b) => teamNameFor(a.team_id).localeCompare(teamNameFor(b.team_id)) || a.name.localeCompare(b.name),
  );
}

export function TeamResponsibleManagement({ initialTeamResponsibles, teams, seasons }: TeamResponsibleManagementProps) {
  const t = useTranslations("masterdata.teamResponsibles");
  const router = useRouter();

  const [teamResponsibles, setTeamResponsibles] = useState(initialTeamResponsibles);
  // The season picked in the page header (only open seasons; null until
  // mounted or when nothing is picked) is the default season filter.
  const { selectedSeasonId: headerSeasonId } = useSelectedSeason();
  // A season chosen on this screen itself overrides the header's — but only
  // while the header stays on the season it was chosen under, so changing
  // the header season makes this screen follow it again.
  const [seasonOverride, setSeasonOverride] = useState<{ value: string; headerSeasonId: number | null } | null>(
    null,
  );
  // Without a header season, fall back to the most recent season (seasons
  // arrive sorted by name, so that's the last one); "all" shows every season.
  const fallbackSeasonFilter =
    headerSeasonId !== null
      ? String(headerSeasonId)
      : seasons.length > 0
        ? String(seasons[seasons.length - 1].id)
        : ALL_VALUE;
  const seasonFilter =
    seasonOverride !== null && seasonOverride.headerSeasonId === headerSeasonId
      ? seasonOverride.value
      : fallbackSeasonFilter;
  const [teamFilter, setTeamFilter] = useState<string>(ALL_VALUE);

  function teamNameFor(teamId: number) {
    return teams.find((team) => team.id === teamId)?.name ?? "";
  }

  function seasonNameFor(seasonId: number) {
    return seasons.find((season) => season.id === seasonId)?.name ?? "";
  }

  // Only the rows matching the chosen season/team are shown.
  const visibleRows = teamResponsibles.filter(
    (row) =>
      (seasonFilter === ALL_VALUE || String(row.season_id) === seasonFilter) &&
      (teamFilter === ALL_VALUE || String(row.team_id) === teamFilter),
  );

  // New entries start with whatever season/team is currently filtered on.
  const defaultTeamId = teamFilter === ALL_VALUE ? null : Number(teamFilter);
  const defaultSeasonId = seasonFilter === ALL_VALUE ? null : Number(seasonFilter);

  function upsert(updated: TeamResponsible) {
    setTeamResponsibles((current) => {
      const exists = current.some((row) => row.id === updated.id);
      const next = exists ? current.map((row) => (row.id === updated.id ? updated : row)) : [...current, updated];
      return sortRows(next, teamNameFor);
    });
    router.refresh();
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight underline">{t("title")}</h1>
          <p className="text-muted-foreground">{t("description")}</p>
        </div>
        <TeamResponsibleFormDialog
          trigger={<Button>{t("newTeamResponsible")}</Button>}
          onSaved={upsert}
          teams={teams}
          seasons={seasons}
          defaultTeamId={defaultTeamId}
          defaultSeasonId={defaultSeasonId}
        />
      </div>

      {/* Filter bar: narrow the table to one season and/or one team. */}
      <div className="flex flex-wrap gap-4">
        <div className="flex w-48 flex-col gap-2">
          <Label htmlFor="team-responsible-season-filter">{t("filterSeason")}</Label>
          <Select
            value={seasonFilter}
            onValueChange={(value) => setSeasonOverride({ value: value ?? ALL_VALUE, headerSeasonId })}
          >
            <SelectTrigger id="team-responsible-season-filter">
              <SelectValue>
                {(value: string | null) =>
                  seasons.find((season) => String(season.id) === value)?.name ?? t("allSeasons")
                }
              </SelectValue>
            </SelectTrigger>
            <SelectContent>
              <SelectItem value={ALL_VALUE}>{t("allSeasons")}</SelectItem>
              {seasons.map((season) => (
                <SelectItem key={season.id} value={String(season.id)}>
                  {season.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div className="flex w-64 flex-col gap-2">
          <Label htmlFor="team-responsible-team-filter">{t("filterTeam")}</Label>
          <Select value={teamFilter} onValueChange={(value) => setTeamFilter(value ?? ALL_VALUE)}>
            <SelectTrigger id="team-responsible-team-filter">
              <SelectValue>
                {(value: string | null) => teams.find((team) => String(team.id) === value)?.name ?? t("allTeams")}
              </SelectValue>
            </SelectTrigger>
            <SelectContent>
              <SelectItem value={ALL_VALUE}>{t("allTeams")}</SelectItem>
              {teams.map((team) => (
                <SelectItem key={team.id} value={String(team.id)}>
                  {team.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>

      <div className="rounded-md border [&>div]:max-h-[65vh] [&>div]:overflow-y-auto">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="sticky top-0 z-20 bg-background font-bold underline">{t("columnTeam")}</TableHead>
              <TableHead className="sticky top-0 z-20 bg-background font-bold underline">{t("columnSeason")}</TableHead>
              <TableHead className="sticky top-0 z-20 bg-background font-bold underline">{t("columnName")}</TableHead>
              <TableHead className="sticky top-0 z-20 bg-background font-bold underline">{t("columnEmail")}</TableHead>
              <TableHead className="sticky top-0 z-20 bg-background font-bold underline">{t("columnPhone")}</TableHead>
              <TableHead className="sticky top-0 z-20 bg-background font-bold underline">{t("columnComments")}</TableHead>
              <TableHead className="sticky top-0 right-0 z-30 bg-background text-right font-bold underline">
                {t("tableActions")}
              </TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {visibleRows.length === 0 && (
              <TableRow>
                <TableCell colSpan={7} className="text-center text-muted-foreground">
                  {t("empty")}
                </TableCell>
              </TableRow>
            )}
            {visibleRows.map((row) => (
              <TableRow key={row.id} className="group">
                <TableCell className="font-medium">{teamNameFor(row.team_id)}</TableCell>
                <TableCell className="text-muted-foreground">{seasonNameFor(row.season_id)}</TableCell>
                <TableCell>{row.name}</TableCell>
                <TableCell className="text-muted-foreground">
                  <a href={`mailto:${row.email}`} className="hover:underline">
                    {row.email}
                  </a>
                </TableCell>
                <TableCell className="text-muted-foreground">
                  <a href={`tel:${row.phone}`} className="hover:underline">
                    {row.phone}
                  </a>
                </TableCell>
                {/* Long comments are cut off here; the full text is in the edit dialog and the tooltip. */}
                <TableCell className="max-w-64 truncate text-muted-foreground" title={row.comments ?? undefined}>
                  {row.comments}
                </TableCell>
                <TableCell className="sticky right-0 z-10 bg-background group-hover:bg-muted/50">
                  <div className="flex justify-end gap-1">
                    <TeamResponsibleFormDialog
                      teamResponsible={row}
                      trigger={
                        <Button variant="ghost" size="icon" aria-label={t("change")} title={t("change")}>
                          <Pencil className="size-4" />
                        </Button>
                      }
                      onSaved={upsert}
                      teams={teams}
                      seasons={seasons}
                      defaultTeamId={defaultTeamId}
                      defaultSeasonId={defaultSeasonId}
                    />
                    <DeleteTeamResponsibleAlertDialog
                      teamResponsible={row}
                      onDeleted={(teamResponsibleId) => {
                        setTeamResponsibles((current) => current.filter((item) => item.id !== teamResponsibleId));
                        router.refresh();
                      }}
                    />
                  </div>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}

interface TeamResponsibleFormDialogProps {
  teamResponsible?: TeamResponsible;
  trigger: React.ReactElement;
  onSaved: (teamResponsible: TeamResponsible) => void;
  teams: NamedOption[];
  seasons: NamedOption[];
  defaultTeamId: number | null;
  defaultSeasonId: number | null;
}

function TeamResponsibleFormDialog({
  teamResponsible,
  trigger,
  onSaved,
  teams,
  seasons,
  defaultTeamId,
  defaultSeasonId,
}: TeamResponsibleFormDialogProps) {
  const t = useTranslations("masterdata.teamResponsibles");
  const isEditing = teamResponsible !== undefined;
  const [isOpen, setIsOpen] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);

  function initialForm(): TeamResponsibleFormState {
    if (teamResponsible) return toFormValues(teamResponsible);
    return { team_id: defaultTeamId, season_id: defaultSeasonId, name: "", email: "", phone: "", comments: "" };
  }

  const [form, setForm] = useState<TeamResponsibleFormState>(initialForm);

  function handleOpenChange(open: boolean) {
    setIsOpen(open);
    if (open) {
      // Start from the latest known values (and current filters) each time
      // the dialog is opened.
      setForm(initialForm());
    }
  }

  function updateField<K extends keyof TeamResponsibleFormState>(field: K, value: TeamResponsibleFormState[K]) {
    setForm((current) => ({ ...current, [field]: value }));
  }

  // Everything except the comments is required.
  const isComplete =
    form.team_id !== null &&
    form.season_id !== null &&
    form.name.trim() !== "" &&
    form.email.trim() !== "" &&
    form.phone.trim() !== "";

  async function handleSubmit() {
    if (form.team_id === null || form.season_id === null) return;
    const payload: TeamResponsibleInput = {
      ...form,
      team_id: form.team_id,
      season_id: form.season_id,
      email: form.email.trim(),
      comments: form.comments.trim() || null,
    };

    setIsSubmitting(true);
    try {
      const saved = isEditing
        ? await updateTeamResponsible(teamResponsible.id, payload)
        : await createTeamResponsible(payload);
      toast.success(isEditing ? t("teamResponsibleUpdated") : t("teamResponsibleCreated"));
      onSaved(saved);
      setIsOpen(false);
    } catch (error) {
      const message = error instanceof ApiError ? error.message : isEditing ? t("updateFailed") : t("createFailed");
      toast.error(message);
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <Dialog open={isOpen} onOpenChange={handleOpenChange}>
      <DialogTrigger render={trigger} />
      <DialogContent className="sm:max-w-xl">
        <DialogHeader>
          <DialogTitle>{isEditing ? t("changeTitle") : t("createTitle")}</DialogTitle>
          <DialogDescription>{isEditing ? t("changeDescription") : t("createDescription")}</DialogDescription>
        </DialogHeader>

        <div className="grid grid-cols-2 gap-4">
          <div className="flex flex-col gap-2">
            <Label htmlFor="team-responsible-team">{t("teamLabel")}</Label>
            <Select
              value={form.team_id ? String(form.team_id) : ""}
              onValueChange={(value) => updateField("team_id", value ? Number(value) : null)}
            >
              <SelectTrigger id="team-responsible-team">
                <SelectValue placeholder={t("selectPlaceholder")}>
                  {(value: string | null) => teams.find((team) => String(team.id) === value)?.name}
                </SelectValue>
              </SelectTrigger>
              <SelectContent>
                {teams.map((team) => (
                  <SelectItem key={team.id} value={String(team.id)}>
                    {team.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="flex flex-col gap-2">
            <Label htmlFor="team-responsible-season">{t("seasonLabel")}</Label>
            <Select
              value={form.season_id ? String(form.season_id) : ""}
              onValueChange={(value) => updateField("season_id", value ? Number(value) : null)}
            >
              <SelectTrigger id="team-responsible-season">
                <SelectValue placeholder={t("selectPlaceholder")}>
                  {(value: string | null) => seasons.find((season) => String(season.id) === value)?.name}
                </SelectValue>
              </SelectTrigger>
              <SelectContent>
                {seasons.map((season) => (
                  <SelectItem key={season.id} value={String(season.id)}>
                    {season.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="col-span-2 flex flex-col gap-2">
            <Label htmlFor="team-responsible-name">{t("nameLabel")}</Label>
            <Input
              id="team-responsible-name"
              value={form.name}
              onChange={(event) => updateField("name", event.target.value)}
            />
          </div>
          <div className="flex flex-col gap-2">
            <Label htmlFor="team-responsible-email">{t("emailLabel")}</Label>
            <Input
              id="team-responsible-email"
              type="email"
              value={form.email}
              onChange={(event) => updateField("email", event.target.value)}
            />
          </div>
          <div className="flex flex-col gap-2">
            <Label htmlFor="team-responsible-phone">{t("phoneLabel")}</Label>
            <Input
              id="team-responsible-phone"
              type="tel"
              value={form.phone}
              onChange={(event) => updateField("phone", event.target.value)}
            />
          </div>
          <div className="col-span-2 flex flex-col gap-2">
            <Label htmlFor="team-responsible-comments">{t("commentsLabel")}</Label>
            <Textarea
              id="team-responsible-comments"
              maxLength={5000}
              value={form.comments}
              onChange={(event) => updateField("comments", event.target.value)}
            />
          </div>
        </div>

        <DialogFooter>
          <Button onClick={handleSubmit} disabled={isSubmitting || !isComplete}>
            {isEditing ? t("change") : t("newTeamResponsible")}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

interface DeleteTeamResponsibleAlertDialogProps {
  teamResponsible: TeamResponsible;
  onDeleted: (teamResponsibleId: number) => void;
}

function DeleteTeamResponsibleAlertDialog({ teamResponsible, onDeleted }: DeleteTeamResponsibleAlertDialogProps) {
  const t = useTranslations("masterdata.teamResponsibles");
  const tCommon = useTranslations("common");
  const [isOpen, setIsOpen] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);

  async function handleConfirmDelete() {
    setIsDeleting(true);
    try {
      await deleteTeamResponsible(teamResponsible.id);
      toast.success(t("teamResponsibleDeleted"));
      onDeleted(teamResponsible.id);
      setIsOpen(false);
    } catch (error) {
      const message = error instanceof ApiError ? error.message : t("deleteFailed");
      toast.error(message);
    } finally {
      setIsDeleting(false);
    }
  }

  return (
    <AlertDialog open={isOpen} onOpenChange={setIsOpen}>
      <AlertDialogTrigger
        render={
          <Button variant="ghost" size="icon" aria-label={t("delete")} title={t("delete")}>
            <Trash2 className="size-4 text-destructive" />
          </Button>
        }
      />
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>{t("deleteConfirmTitle")}</AlertDialogTitle>
          <AlertDialogDescription>
            {t("deleteConfirmDescription", { name: teamResponsible.name })}
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel>{tCommon("cancel")}</AlertDialogCancel>
          <AlertDialogAction variant="destructive" disabled={isDeleting} onClick={handleConfirmDelete}>
            {t("delete")}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}
