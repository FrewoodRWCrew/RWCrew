"use client";

// MasterData's "Teams" screen: a table of teams with add/change/delete,
// following the same dialog/table pattern as products-management.tsx —
// the create/edit dialog covers every field from the reference "Teams"
// screen (naam, Locatie, Leverwijze, Taken, Kernleden, Beschrijving).

import { useState } from "react";
import { Pencil, Trash2 } from "lucide-react";
import { useTranslations } from "next-intl";
import { toast } from "sonner";
import { useRouter } from "@/i18n/navigation";
import { ApiError, createTeam, deleteTeam, updateTeam } from "@/lib/api";
import type { AltsienKernlid, DeliveryMethod, Team, TeamInput, TeamLocation, TeamTask } from "@/lib/types";
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
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { TagMultiSelect } from "@/components/ui/tag-multi-select";
import { Textarea } from "@/components/ui/textarea";

interface TeamManagementProps {
  initialTeams: Team[];
  teamLocations: TeamLocation[];
  deliveryMethods: DeliveryMethod[];
  teamTasks: TeamTask[];
  kernleden: AltsienKernlid[];
}

// Base UI's Select needs every item to have a non-empty value, so "no
// selection" is represented by this sentinel string instead of "".
const NO_SELECTION_VALUE = "none";

const EMPTY_FORM: TeamInput = {
  name: "",
  location_id: null,
  delivery_method_id: null,
  task_ids: [],
  kernlid_ids: [],
  description: "",
  active: true,
};

function toFormValues(team: Team): TeamInput {
  return {
    name: team.name,
    location_id: team.location_id,
    delivery_method_id: team.delivery_method_id,
    task_ids: team.task_ids,
    kernlid_ids: team.kernlid_ids,
    description: team.description ?? "",
    active: team.active,
  };
}

export function TeamManagement({
  initialTeams,
  teamLocations,
  deliveryMethods,
  teamTasks,
  kernleden,
}: TeamManagementProps) {
  const t = useTranslations("masterdata.teams");
  const router = useRouter();

  const [teams, setTeams] = useState(initialTeams);

  function locationLabelFor(locationId: number | null) {
    return teamLocations.find((location) => location.id === locationId)?.location ?? "";
  }

  function deliveryMethodLabelFor(deliveryMethodId: number | null) {
    return deliveryMethods.find((method) => method.id === deliveryMethodId)?.delivery_method ?? "";
  }

  function upsert(updated: Team) {
    setTeams((current) => {
      const exists = current.some((team) => team.id === updated.id);
      return exists
        ? current.map((team) => (team.id === updated.id ? updated : team))
        : [...current, updated].sort((a, b) => a.name.localeCompare(b.name));
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
        <TeamFormDialog
          trigger={<Button>{t("newTeam")}</Button>}
          onSaved={upsert}
          teamLocations={teamLocations}
          deliveryMethods={deliveryMethods}
          teamTasks={teamTasks}
          kernleden={kernleden}
        />
      </div>

      <div className="rounded-md border [&>div]:max-h-[65vh] [&>div]:overflow-y-auto">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="sticky top-0 z-20 bg-background font-bold underline">{t("columnName")}</TableHead>
              <TableHead className="sticky top-0 z-20 bg-background font-bold underline">{t("columnLocation")}</TableHead>
              <TableHead className="sticky top-0 z-20 bg-background font-bold underline">{t("columnDeliveryMethod")}</TableHead>
              <TableHead className="sticky top-0 z-20 bg-background font-bold underline">{t("columnActive")}</TableHead>
              <TableHead className="sticky top-0 right-0 z-30 bg-background text-right font-bold underline">
                {t("tableActions")}
              </TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {teams.map((team) => (
              <TableRow key={team.id} className="group">
                <TableCell className="font-medium">{team.name}</TableCell>
                <TableCell className="text-muted-foreground">{locationLabelFor(team.location_id)}</TableCell>
                <TableCell className="text-muted-foreground">
                  {deliveryMethodLabelFor(team.delivery_method_id)}
                </TableCell>
                <TableCell className="text-muted-foreground">{team.active ? t("activeYes") : t("activeNo")}</TableCell>
                <TableCell className="sticky right-0 z-10 bg-background group-hover:bg-muted/50">
                  <div className="flex justify-end gap-1">
                    <TeamFormDialog
                      team={team}
                      trigger={
                        <Button variant="ghost" size="icon" aria-label={t("change")} title={t("change")}>
                          <Pencil className="size-4" />
                        </Button>
                      }
                      onSaved={upsert}
                      teamLocations={teamLocations}
                      deliveryMethods={deliveryMethods}
                      teamTasks={teamTasks}
                      kernleden={kernleden}
                    />
                    <DeleteTeamAlertDialog
                      team={team}
                      onDeleted={(teamId) => {
                        setTeams((current) => current.filter((item) => item.id !== teamId));
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

interface TeamFormDialogProps {
  team?: Team;
  trigger: React.ReactElement;
  onSaved: (team: Team) => void;
  teamLocations: TeamLocation[];
  deliveryMethods: DeliveryMethod[];
  teamTasks: TeamTask[];
  kernleden: AltsienKernlid[];
}

function TeamFormDialog({
  team,
  trigger,
  onSaved,
  teamLocations,
  deliveryMethods,
  teamTasks,
  kernleden,
}: TeamFormDialogProps) {
  const t = useTranslations("masterdata.teams");
  const isEditing = team !== undefined;
  const [isOpen, setIsOpen] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [form, setForm] = useState<TeamInput>(team ? toFormValues(team) : EMPTY_FORM);

  function handleOpenChange(open: boolean) {
    setIsOpen(open);
    if (open) {
      // Start from the team's latest known values each time the dialog is
      // opened, in case they changed since last time.
      setForm(team ? toFormValues(team) : EMPTY_FORM);
    }
  }

  function updateField<K extends keyof TeamInput>(field: K, value: TeamInput[K]) {
    setForm((current) => ({ ...current, [field]: value }));
  }

  async function handleSubmit() {
    setIsSubmitting(true);
    try {
      const savedTeam = isEditing ? await updateTeam(team.id, form) : await createTeam(form);
      toast.success(isEditing ? t("teamUpdated") : t("teamCreated"));
      onSaved(savedTeam);
      setIsOpen(false);
    } catch (error) {
      const message = error instanceof ApiError ? error.message : isEditing ? t("updateFailed") : t("createFailed");
      toast.error(message);
    } finally {
      setIsSubmitting(false);
    }
  }

  const taskOptions = teamTasks.map((task) => ({ id: task.id, label: task.team_tasks }));
  const kernlidOptions = kernleden.map((kernlid) => ({ id: kernlid.id, label: kernlid.display_name }));

  return (
    <Dialog open={isOpen} onOpenChange={handleOpenChange}>
      <DialogTrigger render={trigger} />
      <DialogContent className="sm:max-w-xl">
        <DialogHeader>
          <DialogTitle>{isEditing ? t("changeTitle") : t("createTitle")}</DialogTitle>
          <DialogDescription>{isEditing ? t("changeDescription") : t("createDescription")}</DialogDescription>
        </DialogHeader>

        <div className="grid grid-cols-2 gap-4">
          <div className="col-span-2 flex flex-col gap-2">
            <Label htmlFor="team-name">{t("nameLabel")}</Label>
            <Input id="team-name" value={form.name} onChange={(event) => updateField("name", event.target.value)} />
          </div>
          <div className="flex flex-col gap-2">
            <Label htmlFor="team-location">{t("locationLabel")}</Label>
            <Select
              value={form.location_id ? String(form.location_id) : NO_SELECTION_VALUE}
              onValueChange={(value) => updateField("location_id", value && value !== NO_SELECTION_VALUE ? Number(value) : null)}
            >
              <SelectTrigger id="team-location">
                <SelectValue>
                  {(value: string | null) =>
                    teamLocations.find((location) => String(location.id) === value)?.location ?? t("noSelection")
                  }
                </SelectValue>
              </SelectTrigger>
              <SelectContent>
                <SelectItem value={NO_SELECTION_VALUE}>{t("noSelection")}</SelectItem>
                {teamLocations.map((location) => (
                  <SelectItem key={location.id} value={String(location.id)}>
                    {location.location}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="flex flex-col gap-2">
            <Label htmlFor="team-delivery-method">{t("deliveryMethodLabel")}</Label>
            <Select
              value={form.delivery_method_id ? String(form.delivery_method_id) : NO_SELECTION_VALUE}
              onValueChange={(value) =>
                updateField("delivery_method_id", value && value !== NO_SELECTION_VALUE ? Number(value) : null)
              }
            >
              <SelectTrigger id="team-delivery-method">
                <SelectValue>
                  {(value: string | null) =>
                    deliveryMethods.find((method) => String(method.id) === value)?.delivery_method ?? t("noSelection")
                  }
                </SelectValue>
              </SelectTrigger>
              <SelectContent>
                <SelectItem value={NO_SELECTION_VALUE}>{t("noSelection")}</SelectItem>
                {deliveryMethods.map((method) => (
                  <SelectItem key={method.id} value={String(method.id)}>
                    {method.delivery_method}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="col-span-2 flex flex-col gap-2">
            <Label htmlFor="team-tasks">{t("tasksLabel")}</Label>
            <TagMultiSelect
              id="team-tasks"
              options={taskOptions}
              selectedIds={form.task_ids ?? []}
              onChange={(ids) => updateField("task_ids", ids)}
              placeholder={t("tasksPlaceholder")}
            />
          </div>
          <div className="col-span-2 flex flex-col gap-2">
            <Label htmlFor="team-members">{t("membersLabel")}</Label>
            <TagMultiSelect
              id="team-members"
              options={kernlidOptions}
              selectedIds={form.kernlid_ids ?? []}
              onChange={(ids) => updateField("kernlid_ids", ids)}
              placeholder={t("membersPlaceholder")}
            />
          </div>
          <div className="col-span-2 flex flex-col gap-2">
            <Label htmlFor="team-description">{t("descriptionLabel")}</Label>
            <Textarea
              id="team-description"
              value={form.description ?? ""}
              onChange={(event) => updateField("description", event.target.value)}
            />
          </div>
          <div className="col-span-2 flex items-center gap-2">
            <Checkbox
              id="team-active"
              checked={form.active ?? true}
              onCheckedChange={(checked) => updateField("active", checked === true)}
            />
            <Label htmlFor="team-active">{t("activeLabel")}</Label>
          </div>
        </div>

        <DialogFooter>
          <Button onClick={handleSubmit} disabled={isSubmitting || !form.name}>
            {isEditing ? t("change") : t("newTeam")}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

interface DeleteTeamAlertDialogProps {
  team: Team;
  onDeleted: (teamId: number) => void;
}

function DeleteTeamAlertDialog({ team, onDeleted }: DeleteTeamAlertDialogProps) {
  const t = useTranslations("masterdata.teams");
  const tCommon = useTranslations("common");
  const [isOpen, setIsOpen] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);

  async function handleConfirmDelete() {
    setIsDeleting(true);
    try {
      await deleteTeam(team.id);
      toast.success(t("teamDeleted"));
      onDeleted(team.id);
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
          <AlertDialogDescription>{t("deleteConfirmDescription", { name: team.name })}</AlertDialogDescription>
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
