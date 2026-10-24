"use client";

// KarTracker's "Speciale levertoeren" screen: the special delivery tours
// (e.g. "Kleine wastoer", "Ijsblokken") that regularly pass by teams, with
// add/change/delete. Teams are linked to a tour on MasterData's team fiche;
// this screen only shows them. Same dialog/table pattern as
// components/module-9/team-management.tsx.

import { useState } from "react";
import { Pencil, Trash2 } from "lucide-react";
import { useTranslations } from "next-intl";
import { toast } from "sonner";
import { useRouter } from "@/i18n/navigation";
import { ApiError, createSpecialTour, deleteSpecialTour, updateSpecialTour } from "@/lib/api";
import type { KarTrackerSpecialTour, KarTrackerSpecialTourInput } from "@/lib/types";
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
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Textarea } from "@/components/ui/textarea";

interface SpecialTourManagementProps {
  initialTours: KarTrackerSpecialTour[];
}

const EMPTY_FORM: KarTrackerSpecialTourInput = { name: "", description: "", active: true };

function toFormValues(tour: KarTrackerSpecialTour): KarTrackerSpecialTourInput {
  return { name: tour.name, description: tour.description ?? "", active: tour.active };
}

export function SpecialTourManagement({ initialTours }: SpecialTourManagementProps) {
  const t = useTranslations("karTracker.specialTours");
  const router = useRouter();

  const [tours, setTours] = useState(initialTours);

  // Put a created/changed tour in the list, keeping it sorted by name.
  function upsert(updated: KarTrackerSpecialTour) {
    setTours((current) => {
      const exists = current.some((tour) => tour.id === updated.id);
      return exists
        ? current.map((tour) => (tour.id === updated.id ? updated : tour))
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
        <SpecialTourFormDialog trigger={<Button>{t("newTour")}</Button>} onSaved={upsert} />
      </div>

      <div className="rounded-md border [&>div]:max-h-[65vh] [&>div]:overflow-y-auto">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="sticky top-0 z-20 bg-background font-bold underline">{t("columnName")}</TableHead>
              <TableHead className="sticky top-0 z-20 bg-background font-bold underline">
                {t("columnDescription")}
              </TableHead>
              <TableHead className="sticky top-0 z-20 bg-background font-bold underline">{t("columnTeams")}</TableHead>
              <TableHead className="sticky top-0 z-20 bg-background font-bold underline">{t("columnActive")}</TableHead>
              <TableHead className="sticky top-0 right-0 z-30 bg-background text-right font-bold underline">
                {t("tableActions")}
              </TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {tours.length === 0 && (
              <TableRow>
                <TableCell colSpan={5} className="text-center text-muted-foreground">
                  {t("empty")}
                </TableCell>
              </TableRow>
            )}
            {tours.map((tour) => (
              <TableRow key={tour.id} className="group">
                <TableCell className="font-medium">{tour.name}</TableCell>
                <TableCell className="max-w-xs truncate text-muted-foreground" title={tour.description ?? undefined}>
                  {tour.description}
                </TableCell>
                <TableCell className="text-muted-foreground">
                  {tour.team_names.length > 0 ? tour.team_names.join(", ") : t("noTeams")}
                </TableCell>
                <TableCell className="text-muted-foreground">{tour.active ? t("activeYes") : t("activeNo")}</TableCell>
                <TableCell className="sticky right-0 z-10 bg-background group-hover:bg-muted/50">
                  <div className="flex justify-end gap-1">
                    <SpecialTourFormDialog
                      tour={tour}
                      trigger={
                        <Button variant="ghost" size="icon" aria-label={t("change")} title={t("change")}>
                          <Pencil className="size-4" />
                        </Button>
                      }
                      onSaved={upsert}
                    />
                    <DeleteSpecialTourAlertDialog
                      tour={tour}
                      onDeleted={(tourId) => {
                        setTours((current) => current.filter((item) => item.id !== tourId));
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

interface SpecialTourFormDialogProps {
  tour?: KarTrackerSpecialTour;
  trigger: React.ReactElement;
  onSaved: (tour: KarTrackerSpecialTour) => void;
}

function SpecialTourFormDialog({ tour, trigger, onSaved }: SpecialTourFormDialogProps) {
  const t = useTranslations("karTracker.specialTours");
  const isEditing = tour !== undefined;
  const [isOpen, setIsOpen] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [form, setForm] = useState<KarTrackerSpecialTourInput>(tour ? toFormValues(tour) : EMPTY_FORM);

  function handleOpenChange(open: boolean) {
    setIsOpen(open);
    if (open) {
      // Start from the tour's latest known values each time the dialog opens.
      setForm(tour ? toFormValues(tour) : EMPTY_FORM);
    }
  }

  async function handleSubmit() {
    setIsSubmitting(true);
    try {
      // An empty description is stored as "none".
      const payload = { ...form, description: form.description?.trim() ? form.description : null };
      const saved = isEditing ? await updateSpecialTour(tour.id, payload) : await createSpecialTour(payload);
      toast.success(isEditing ? t("tourUpdated") : t("tourCreated"));
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
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{isEditing ? t("changeTitle") : t("createTitle")}</DialogTitle>
          <DialogDescription>{isEditing ? t("changeDescription") : t("createDescription")}</DialogDescription>
        </DialogHeader>

        <div className="flex flex-col gap-4">
          <div className="flex flex-col gap-2">
            <Label htmlFor="special-tour-name">{t("nameLabel")}</Label>
            <Input
              id="special-tour-name"
              value={form.name}
              onChange={(event) => setForm((current) => ({ ...current, name: event.target.value }))}
            />
          </div>
          <div className="flex flex-col gap-2">
            <Label htmlFor="special-tour-description">{t("descriptionLabel")}</Label>
            <Textarea
              id="special-tour-description"
              value={form.description ?? ""}
              placeholder={t("descriptionPlaceholder")}
              onChange={(event) => setForm((current) => ({ ...current, description: event.target.value }))}
            />
          </div>
          <div className="flex items-center gap-2">
            <Checkbox
              id="special-tour-active"
              checked={form.active}
              onCheckedChange={(checked) => setForm((current) => ({ ...current, active: checked === true }))}
            />
            <Label htmlFor="special-tour-active">{t("activeLabel")}</Label>
          </div>
        </div>

        <DialogFooter>
          <Button onClick={handleSubmit} disabled={isSubmitting || !form.name.trim()}>
            {isEditing ? t("change") : t("newTour")}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

interface DeleteSpecialTourAlertDialogProps {
  tour: KarTrackerSpecialTour;
  onDeleted: (tourId: number) => void;
}

function DeleteSpecialTourAlertDialog({ tour, onDeleted }: DeleteSpecialTourAlertDialogProps) {
  const t = useTranslations("karTracker.specialTours");
  const tCommon = useTranslations("common");
  const [isOpen, setIsOpen] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);

  async function handleConfirmDelete() {
    setIsDeleting(true);
    try {
      await deleteSpecialTour(tour.id);
      toast.success(t("tourDeleted"));
      onDeleted(tour.id);
      setIsOpen(false);
    } catch (error) {
      // Still linked to a team: the backend refuses (deactivate instead).
      const message =
        error instanceof ApiError && error.status === 400 ? t("deleteInUse") : error instanceof ApiError ? error.message : t("deleteFailed");
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
          <AlertDialogDescription>{t("deleteConfirmDescription", { name: tour.name })}</AlertDialogDescription>
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
