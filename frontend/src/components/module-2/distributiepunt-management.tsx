"use client";

// KarTracker's "Distributiepunten" screen: the distribution-point master
// data — a table with add/change/delete. Modeled on KarManagement (a
// bespoke, multi-field CRUD screen), since it has an Altsien Kernlid
// dropdown alongside plain fields, which the shared LookupManagement
// component (single name field only) can't handle. Altsien Kernlid is
// picked from module-9's existing Altsien Kernleden master data
// (cross-module, same pattern as KarManagement's own Team dropdown).

import { useState } from "react";
import { Pencil, Trash2 } from "lucide-react";
import { useTranslations } from "next-intl";
import { toast } from "sonner";
import { useRouter } from "@/i18n/navigation";
import { ApiError, createDistributiepunt, deleteDistributiepunt, updateDistributiepunt } from "@/lib/api";
import type { AltsienKernlid, KarTrackerDistributiepunt, KarTrackerDistributiepuntInput } from "@/lib/types";
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

interface DistributiepuntManagementProps {
  initialDistributiepunten: KarTrackerDistributiepunt[];
  altsienKernleden: AltsienKernlid[];
}

// Base UI's Select needs every item to have a non-empty value, so "no
// kernlid assigned" (altsien_kernlid_id is optional) is represented by
// this sentinel string instead of "" — same pattern as KarManagement's
// own NO_TEAM_VALUE.
const NO_KERNLID_VALUE = "none";

const EMPTY_FORM: KarTrackerDistributiepuntInput = {
  name: "",
  latitude: null,
  longitude: null,
  terrein_positie: null,
  altsien_kernlid_id: null,
};

function toFormValues(distributiepunt: KarTrackerDistributiepunt): KarTrackerDistributiepuntInput {
  return {
    name: distributiepunt.name,
    latitude: distributiepunt.latitude,
    longitude: distributiepunt.longitude,
    terrein_positie: distributiepunt.terrein_positie,
    altsien_kernlid_id: distributiepunt.altsien_kernlid_id,
  };
}

function kernlidLabel(kernlid: AltsienKernlid) {
  return `${kernlid.first_name} ${kernlid.name}`;
}

export function DistributiepuntManagement({
  initialDistributiepunten,
  altsienKernleden,
}: DistributiepuntManagementProps) {
  const t = useTranslations("karTracker.distributiepunten");
  const router = useRouter();

  const [distributiepunten, setDistributiepunten] = useState(initialDistributiepunten);

  function kernlidLabelFor(kernlidId: number | null) {
    if (kernlidId === null) return "";
    const kernlid = altsienKernleden.find((item) => item.id === kernlidId);
    return kernlid ? kernlidLabel(kernlid) : "";
  }

  function upsert(updated: KarTrackerDistributiepunt) {
    setDistributiepunten((current) => {
      const exists = current.some((item) => item.id === updated.id);
      return exists
        ? current.map((item) => (item.id === updated.id ? updated : item)).sort((a, b) => a.name.localeCompare(b.name))
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
        <DistributiepuntFormDialog
          trigger={<Button>{t("newDistributiepunt")}</Button>}
          onSaved={upsert}
          altsienKernleden={altsienKernleden}
        />
      </div>

      <div className="rounded-md border [&>div]:max-h-[65vh] [&>div]:overflow-y-auto">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="sticky top-0 z-20 bg-background font-bold underline">{t("columnName")}</TableHead>
              <TableHead className="sticky top-0 z-20 bg-background font-bold underline">{t("columnLatitude")}</TableHead>
              <TableHead className="sticky top-0 z-20 bg-background font-bold underline">{t("columnLongitude")}</TableHead>
              <TableHead className="sticky top-0 z-20 bg-background font-bold underline">
                {t("columnTerreinPositie")}
              </TableHead>
              <TableHead className="sticky top-0 z-20 bg-background font-bold underline">
                {t("columnAltsienKernlid")}
              </TableHead>
              <TableHead className="sticky top-0 right-0 z-30 bg-background text-right font-bold underline">
                {t("tableActions")}
              </TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {distributiepunten.map((distributiepunt) => (
              <TableRow key={distributiepunt.id} className="group">
                <TableCell className="font-medium">{distributiepunt.name}</TableCell>
                <TableCell className="text-muted-foreground">{distributiepunt.latitude ?? ""}</TableCell>
                <TableCell className="text-muted-foreground">{distributiepunt.longitude ?? ""}</TableCell>
                <TableCell className="text-muted-foreground">{distributiepunt.terrein_positie ?? ""}</TableCell>
                <TableCell className="text-muted-foreground">
                  {kernlidLabelFor(distributiepunt.altsien_kernlid_id)}
                </TableCell>
                <TableCell className="sticky right-0 z-10 bg-background group-hover:bg-muted/50">
                  <div className="flex justify-end gap-1">
                    <DistributiepuntFormDialog
                      distributiepunt={distributiepunt}
                      trigger={
                        <Button variant="ghost" size="icon" aria-label={t("change")} title={t("change")}>
                          <Pencil className="size-4" />
                        </Button>
                      }
                      onSaved={upsert}
                      altsienKernleden={altsienKernleden}
                    />
                    <DeleteDistributiepuntAlertDialog
                      distributiepunt={distributiepunt}
                      onDeleted={(id) => {
                        setDistributiepunten((current) => current.filter((item) => item.id !== id));
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

interface DistributiepuntFormDialogProps {
  distributiepunt?: KarTrackerDistributiepunt;
  trigger: React.ReactElement;
  onSaved: (distributiepunt: KarTrackerDistributiepunt) => void;
  altsienKernleden: AltsienKernlid[];
}

function DistributiepuntFormDialog({ distributiepunt, trigger, onSaved, altsienKernleden }: DistributiepuntFormDialogProps) {
  const t = useTranslations("karTracker.distributiepunten");
  const isEditing = distributiepunt !== undefined;
  const [isOpen, setIsOpen] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [form, setForm] = useState<KarTrackerDistributiepuntInput>(
    distributiepunt ? toFormValues(distributiepunt) : EMPTY_FORM,
  );

  function handleOpenChange(open: boolean) {
    setIsOpen(open);
    if (open) {
      // Start from the distribution point's latest known values each time
      // the dialog is opened, in case they changed since last time.
      setForm(distributiepunt ? toFormValues(distributiepunt) : EMPTY_FORM);
    }
  }

  function updateField<K extends keyof KarTrackerDistributiepuntInput>(field: K, value: KarTrackerDistributiepuntInput[K]) {
    setForm((current) => ({ ...current, [field]: value }));
  }

  async function handleSubmit() {
    setIsSubmitting(true);
    try {
      const saved = isEditing
        ? await updateDistributiepunt(distributiepunt.id, form)
        : await createDistributiepunt(form);
      toast.success(isEditing ? t("distributiepuntUpdated") : t("distributiepuntCreated"));
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
          <div className="col-span-2 flex flex-col gap-2">
            <Label htmlFor="distributiepunt-name">{t("nameLabel")}</Label>
            <Input
              id="distributiepunt-name"
              value={form.name}
              onChange={(event) => updateField("name", event.target.value)}
            />
          </div>
          <div className="flex flex-col gap-2">
            <Label htmlFor="distributiepunt-latitude">{t("latitudeLabel")}</Label>
            <Input
              id="distributiepunt-latitude"
              type="number"
              step="any"
              value={form.latitude ?? ""}
              onChange={(event) => updateField("latitude", event.target.value ? Number(event.target.value) : null)}
            />
          </div>
          <div className="flex flex-col gap-2">
            <Label htmlFor="distributiepunt-longitude">{t("longitudeLabel")}</Label>
            <Input
              id="distributiepunt-longitude"
              type="number"
              step="any"
              value={form.longitude ?? ""}
              onChange={(event) => updateField("longitude", event.target.value ? Number(event.target.value) : null)}
            />
          </div>
          <div className="flex flex-col gap-2">
            <Label htmlFor="distributiepunt-terrein-positie">{t("terreinPositieLabel")}</Label>
            <Input
              id="distributiepunt-terrein-positie"
              value={form.terrein_positie ?? ""}
              onChange={(event) => updateField("terrein_positie", event.target.value || null)}
            />
          </div>
          <div className="flex flex-col gap-2">
            <Label htmlFor="distributiepunt-altsien-kernlid">{t("altsienKernlidLabel")}</Label>
            <Select
              value={form.altsien_kernlid_id ? String(form.altsien_kernlid_id) : NO_KERNLID_VALUE}
              onValueChange={(value) =>
                updateField("altsien_kernlid_id", value && value !== NO_KERNLID_VALUE ? Number(value) : null)
              }
            >
              <SelectTrigger id="distributiepunt-altsien-kernlid">
                <SelectValue>
                  {(value: string | null) => {
                    const kernlid = altsienKernleden.find((item) => String(item.id) === value);
                    return kernlid ? kernlidLabel(kernlid) : t("noKernlid");
                  }}
                </SelectValue>
              </SelectTrigger>
              <SelectContent>
                <SelectItem value={NO_KERNLID_VALUE}>{t("noKernlid")}</SelectItem>
                {altsienKernleden.map((kernlid) => (
                  <SelectItem key={kernlid.id} value={String(kernlid.id)}>
                    {kernlidLabel(kernlid)}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>

        <DialogFooter>
          <Button onClick={handleSubmit} disabled={isSubmitting || !form.name.trim()}>
            {isEditing ? t("change") : t("newDistributiepunt")}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

interface DeleteDistributiepuntAlertDialogProps {
  distributiepunt: KarTrackerDistributiepunt;
  onDeleted: (distributiepuntId: number) => void;
}

function DeleteDistributiepuntAlertDialog({ distributiepunt, onDeleted }: DeleteDistributiepuntAlertDialogProps) {
  const t = useTranslations("karTracker.distributiepunten");
  const tCommon = useTranslations("common");
  const [isOpen, setIsOpen] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);

  async function handleConfirmDelete() {
    setIsDeleting(true);
    try {
      await deleteDistributiepunt(distributiepunt.id);
      toast.success(t("distributiepuntDeleted"));
      onDeleted(distributiepunt.id);
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
          <AlertDialogDescription>{t("deleteConfirmDescription", { name: distributiepunt.name })}</AlertDialogDescription>
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
