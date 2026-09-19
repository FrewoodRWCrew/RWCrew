"use client";

// MasterData's "Festivals" screen: a table of festivals with add/change/
// delete, following the same dialog/table pattern as products-management.tsx.
// Unlike Product's optional lookup fields, a festival's Season is required —
// there's no "no selection" option, and the submit button stays disabled
// until every field (including a chosen season) is filled in.

import { useState } from "react";
import { Pencil, Trash2 } from "lucide-react";
import { useTranslations } from "next-intl";
import { toast } from "sonner";
import { useRouter } from "@/i18n/navigation";
import { ApiError, createFestival, deleteFestival, updateFestival } from "@/lib/api";
import type { Festival, FestivalInput, Season } from "@/lib/types";
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

interface FestivalManagementProps {
  initialFestivals: Festival[];
  seasons: Season[];
}

// The form's own shape allows season_id to be null while the user hasn't
// picked one yet — FestivalInput itself keeps season_id required, since
// that's the actual wire contract sent to the backend.
interface FestivalFormState extends Omit<FestivalInput, "season_id"> {
  season_id: number | null;
}

const EMPTY_FORM: FestivalFormState = {
  name: "",
  start_date: "",
  end_date: "",
  season_id: null,
  active: true,
};

function toFormValues(festival: Festival): FestivalFormState {
  return {
    name: festival.name,
    start_date: festival.start_date,
    end_date: festival.end_date,
    season_id: festival.season_id,
    active: festival.active,
  };
}

function formatDate(isoDate: string): string {
  return isoDate.slice(0, 10);
}

export function FestivalManagement({ initialFestivals, seasons }: FestivalManagementProps) {
  const t = useTranslations("masterdata.festival");
  const router = useRouter();

  const [festivals, setFestivals] = useState(initialFestivals);

  function seasonLabelFor(seasonId: number) {
    return seasons.find((season) => season.id === seasonId)?.name ?? "";
  }

  function upsert(updated: Festival) {
    setFestivals((current) => {
      const exists = current.some((festival) => festival.id === updated.id);
      return exists
        ? current.map((festival) => (festival.id === updated.id ? updated : festival))
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
        <FestivalFormDialog trigger={<Button>{t("newFestival")}</Button>} onSaved={upsert} seasons={seasons} />
      </div>

      <div className="rounded-md border [&>div]:max-h-[65vh] [&>div]:overflow-y-auto">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="sticky top-0 z-20 bg-background font-bold underline">{t("columnName")}</TableHead>
              <TableHead className="sticky top-0 z-20 bg-background font-bold underline">{t("columnStartDate")}</TableHead>
              <TableHead className="sticky top-0 z-20 bg-background font-bold underline">{t("columnEndDate")}</TableHead>
              <TableHead className="sticky top-0 z-20 bg-background font-bold underline">{t("columnSeason")}</TableHead>
              <TableHead className="sticky top-0 z-20 bg-background font-bold underline">{t("columnActive")}</TableHead>
              <TableHead className="sticky top-0 right-0 z-30 bg-background text-right font-bold underline">
                {t("tableActions")}
              </TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {festivals.map((festival) => (
              <TableRow key={festival.id} className="group">
                <TableCell className="font-medium">{festival.name}</TableCell>
                <TableCell className="text-muted-foreground">{formatDate(festival.start_date)}</TableCell>
                <TableCell className="text-muted-foreground">{formatDate(festival.end_date)}</TableCell>
                <TableCell className="text-muted-foreground">{seasonLabelFor(festival.season_id)}</TableCell>
                <TableCell className="text-muted-foreground">
                  {festival.active ? t("activeYes") : t("activeNo")}
                </TableCell>
                <TableCell className="sticky right-0 z-10 bg-background group-hover:bg-muted/50">
                  <div className="flex justify-end gap-1">
                    <FestivalFormDialog
                      festival={festival}
                      trigger={
                        <Button variant="ghost" size="icon" aria-label={t("change")} title={t("change")}>
                          <Pencil className="size-4" />
                        </Button>
                      }
                      onSaved={upsert}
                      seasons={seasons}
                    />
                    <DeleteFestivalAlertDialog
                      festival={festival}
                      onDeleted={(festivalId) => {
                        setFestivals((current) => current.filter((item) => item.id !== festivalId));
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

interface FestivalFormDialogProps {
  festival?: Festival;
  trigger: React.ReactElement;
  onSaved: (festival: Festival) => void;
  seasons: Season[];
}

function FestivalFormDialog({ festival, trigger, onSaved, seasons }: FestivalFormDialogProps) {
  const t = useTranslations("masterdata.festival");
  const isEditing = festival !== undefined;
  const [isOpen, setIsOpen] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [form, setForm] = useState<FestivalFormState>(festival ? toFormValues(festival) : EMPTY_FORM);

  function handleOpenChange(open: boolean) {
    setIsOpen(open);
    if (open) {
      // Start from the festival's latest known values each time the
      // dialog is opened, in case they changed since last time.
      setForm(festival ? toFormValues(festival) : EMPTY_FORM);
    }
  }

  function updateField<K extends keyof FestivalFormState>(field: K, value: FestivalFormState[K]) {
    setForm((current) => ({ ...current, [field]: value }));
  }

  async function handleSubmit() {
    if (form.season_id === null) return;
    const payload: FestivalInput = { ...form, season_id: form.season_id };

    setIsSubmitting(true);
    try {
      const savedFestival = isEditing ? await updateFestival(festival.id, payload) : await createFestival(payload);
      toast.success(isEditing ? t("festivalUpdated") : t("festivalCreated"));
      onSaved(savedFestival);
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
          <div className="col-span-2 flex flex-col gap-2">
            <Label htmlFor="festival-name">{t("nameLabel")}</Label>
            <Input
              id="festival-name"
              value={form.name}
              onChange={(event) => updateField("name", event.target.value)}
            />
          </div>
          <div className="flex flex-col gap-2">
            <Label htmlFor="festival-start-date">{t("startDateLabel")}</Label>
            <Input
              id="festival-start-date"
              type="date"
              value={form.start_date}
              onChange={(event) => updateField("start_date", event.target.value)}
            />
          </div>
          <div className="flex flex-col gap-2">
            <Label htmlFor="festival-end-date">{t("endDateLabel")}</Label>
            <Input
              id="festival-end-date"
              type="date"
              value={form.end_date}
              onChange={(event) => updateField("end_date", event.target.value)}
            />
          </div>
          <div className="col-span-2 flex flex-col gap-2">
            <Label htmlFor="festival-season">{t("seasonLabel")}</Label>
            <Select
              value={form.season_id ? String(form.season_id) : ""}
              onValueChange={(value) => updateField("season_id", value ? Number(value) : null)}
            >
              <SelectTrigger id="festival-season">
                <SelectValue>
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
          <div className="col-span-2 flex items-center gap-2">
            <Checkbox
              id="festival-active"
              checked={form.active}
              onCheckedChange={(checked) => updateField("active", checked === true)}
            />
            <Label htmlFor="festival-active">{t("activeLabel")}</Label>
          </div>
        </div>

        <DialogFooter>
          <Button
            onClick={handleSubmit}
            disabled={isSubmitting || !form.name || !form.start_date || !form.end_date || !form.season_id}
          >
            {isEditing ? t("change") : t("newFestival")}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

interface DeleteFestivalAlertDialogProps {
  festival: Festival;
  onDeleted: (festivalId: number) => void;
}

function DeleteFestivalAlertDialog({ festival, onDeleted }: DeleteFestivalAlertDialogProps) {
  const t = useTranslations("masterdata.festival");
  const tCommon = useTranslations("common");
  const [isOpen, setIsOpen] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);

  async function handleConfirmDelete() {
    setIsDeleting(true);
    try {
      await deleteFestival(festival.id);
      toast.success(t("festivalDeleted"));
      onDeleted(festival.id);
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
          <AlertDialogDescription>{t("deleteConfirmDescription", { name: festival.name })}</AlertDialogDescription>
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
