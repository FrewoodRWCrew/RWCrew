"use client";

// MasterData's "Seasons" screen: a table of seasons with add/change/delete,
// following the same dialog/table pattern as
// module-3/intervention-status-management.tsx's own StatusFormDialog. Used
// to be a thin wrapper around the shared LookupManagement component (see
// components/module-9/lookup-management.tsx), but that component is
// deliberately single-field and shared by several other lookup screens
// (ProductType, Warehouses, ...) that must not gain this extra field, so
// this screen now has its own bespoke form for its 2 fields: name and
// "periode open" checkbox.

import { useState } from "react";
import { Pencil, Trash2 } from "lucide-react";
import { useTranslations } from "next-intl";
import { toast } from "sonner";
import { useRouter } from "@/i18n/navigation";
import { ApiError, createSeason, deleteSeason, updateSeason } from "@/lib/api";
import type { Season, SeasonInput } from "@/lib/types";
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
import { Label } from "@/components/ui/label";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";

interface SeasonManagementProps {
  initialSeasons: Season[];
}

const EMPTY_FORM: SeasonInput = { name: "", periode_open: false };

function toFormValues(item: Season): SeasonInput {
  return { name: item.name, periode_open: item.periode_open };
}

export function SeasonManagement({ initialSeasons }: SeasonManagementProps) {
  const t = useTranslations("masterdata.season");
  const router = useRouter();

  const [seasons, setSeasons] = useState(initialSeasons);

  function upsert(updated: Season) {
    setSeasons((current) => {
      const exists = current.some((item) => item.id === updated.id);
      const next = exists ? current.map((item) => (item.id === updated.id ? updated : item)) : [...current, updated];
      return next.sort((a, b) => a.name.localeCompare(b.name));
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
        <SeasonFormDialog trigger={<Button>{t("newSeason")}</Button>} onSaved={upsert} />
      </div>

      <div className="rounded-md border [&>div]:max-h-[65vh] [&>div]:overflow-y-auto">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="sticky top-0 z-20 bg-background font-bold underline">{t("tableName")}</TableHead>
              <TableHead className="sticky top-0 z-20 bg-background font-bold underline">
                {t("columnPeriodeOpen")}
              </TableHead>
              <TableHead className="sticky top-0 right-0 z-30 bg-background text-right font-bold underline">
                {t("tableActions")}
              </TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {seasons.map((item) => (
              <TableRow key={item.id} className="group">
                <TableCell className="font-medium">{item.name}</TableCell>
                <TableCell className="text-muted-foreground">
                  {item.periode_open ? t("periodeOpenYes") : t("periodeOpenNo")}
                </TableCell>
                <TableCell className="sticky right-0 z-10 bg-background group-hover:bg-muted/50">
                  <div className="flex justify-end gap-1">
                    <SeasonFormDialog
                      item={item}
                      trigger={
                        <Button variant="ghost" size="icon" aria-label={t("change")} title={t("change")}>
                          <Pencil className="size-4" />
                        </Button>
                      }
                      onSaved={upsert}
                    />
                    <DeleteSeasonAlertDialog
                      item={item}
                      onDeleted={(deletedId) => {
                        setSeasons((current) => current.filter((current_item) => current_item.id !== deletedId));
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

interface SeasonFormDialogProps {
  item?: Season;
  trigger: React.ReactElement;
  onSaved: (item: Season) => void;
}

function SeasonFormDialog({ item, trigger, onSaved }: SeasonFormDialogProps) {
  const t = useTranslations("masterdata.season");
  const isEditing = item !== undefined;
  const [isOpen, setIsOpen] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [form, setForm] = useState<SeasonInput>(item ? toFormValues(item) : EMPTY_FORM);

  function handleOpenChange(open: boolean) {
    setIsOpen(open);
    if (open) {
      // Start from the season's latest known values each time the dialog
      // is opened, in case they changed since last time.
      setForm(item ? toFormValues(item) : EMPTY_FORM);
    }
  }

  function updateField<K extends keyof SeasonInput>(field: K, value: SeasonInput[K]) {
    setForm((current) => ({ ...current, [field]: value }));
  }

  async function handleSubmit() {
    setIsSubmitting(true);
    try {
      const payload: SeasonInput = { ...form, name: form.name.trim() };
      const savedItem = isEditing ? await updateSeason(item.id, payload) : await createSeason(payload);
      toast.success(isEditing ? t("seasonUpdated") : t("seasonCreated"));
      onSaved(savedItem);
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
            <Label htmlFor="season-name">{t("nameLabel")}</Label>
            <Input id="season-name" value={form.name} onChange={(event) => updateField("name", event.target.value)} />
          </div>

          <div className="flex items-center gap-2">
            <Checkbox
              id="season-periode-open"
              checked={form.periode_open}
              onCheckedChange={(checked) => updateField("periode_open", checked === true)}
            />
            <Label htmlFor="season-periode-open">{t("periodeOpenLabel")}</Label>
          </div>
        </div>

        <DialogFooter>
          <Button onClick={handleSubmit} disabled={isSubmitting || !form.name.trim()}>
            {isEditing ? t("change") : t("newSeason")}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

interface DeleteSeasonAlertDialogProps {
  item: Season;
  onDeleted: (itemId: number) => void;
}

function DeleteSeasonAlertDialog({ item, onDeleted }: DeleteSeasonAlertDialogProps) {
  const t = useTranslations("masterdata.season");
  const tCommon = useTranslations("common");
  const [isOpen, setIsOpen] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);

  async function handleConfirmDelete() {
    setIsDeleting(true);
    try {
      await deleteSeason(item.id);
      toast.success(t("seasonDeleted"));
      onDeleted(item.id);
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
          <AlertDialogDescription>{t("deleteConfirmDescription", { name: item.name })}</AlertDialogDescription>
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
