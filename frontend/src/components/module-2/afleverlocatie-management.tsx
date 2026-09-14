"use client";

// KarTracker's "Afleverlocatie" screen: the delivery-location master data —
// a table with add/change/delete. Modeled on KarManagement (a bespoke,
// multi-field CRUD screen): Zone and Distributiepunt are required
// dropdowns sourced from this module's own master data, Altsien Kernlid is
// an optional dropdown sourced from module-9's existing Altsien Kernleden
// (cross-module, same pattern as KarManagement's own Team dropdown).

import { useState } from "react";
import { Pencil, Trash2 } from "lucide-react";
import { useTranslations } from "next-intl";
import { toast } from "sonner";
import { useRouter } from "@/i18n/navigation";
import { ApiError, createAfleverlocatie, deleteAfleverlocatie, updateAfleverlocatie } from "@/lib/api";
import type {
  AltsienKernlid,
  KarTrackerAfleverlocatie,
  KarTrackerAfleverlocatieInput,
  KarTrackerDistributiepunt,
  KarTrackerZone,
} from "@/lib/types";
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

interface AfleverlocatieManagementProps {
  initialAfleverlocaties: KarTrackerAfleverlocatie[];
  zones: KarTrackerZone[];
  distributiepunten: KarTrackerDistributiepunt[];
  altsienKernleden: AltsienKernlid[];
}

// Base UI's Select needs every item to have a non-empty value, so "no
// kernlid assigned" (altsien_kernlid_id is optional) is represented by
// this sentinel string instead of "" — same pattern as KarManagement's
// own NO_TEAM_VALUE.
const NO_KERNLID_VALUE = "none";

// The form's own shape allows zone_id/distributiepunt_id to be null while
// the user hasn't picked one yet — KarTrackerAfleverlocatieInput itself
// keeps them required, since that's the actual wire contract sent to the
// backend.
interface AfleverlocatieFormState extends Omit<KarTrackerAfleverlocatieInput, "zone_id" | "distributiepunt_id"> {
  zone_id: number | null;
  distributiepunt_id: number | null;
}

const EMPTY_FORM: AfleverlocatieFormState = {
  name: "",
  description: null,
  zone_id: null,
  distributiepunt_id: null,
  latitude: null,
  longitude: null,
  terrein_positie: null,
  altsien_kernlid_id: null,
};

function toFormValues(afleverlocatie: KarTrackerAfleverlocatie): AfleverlocatieFormState {
  return {
    name: afleverlocatie.name,
    description: afleverlocatie.description,
    zone_id: afleverlocatie.zone_id,
    distributiepunt_id: afleverlocatie.distributiepunt_id,
    latitude: afleverlocatie.latitude,
    longitude: afleverlocatie.longitude,
    terrein_positie: afleverlocatie.terrein_positie,
    altsien_kernlid_id: afleverlocatie.altsien_kernlid_id,
  };
}

function kernlidLabel(kernlid: AltsienKernlid) {
  return `${kernlid.first_name} ${kernlid.name}`;
}

export function AfleverlocatieManagement({
  initialAfleverlocaties,
  zones,
  distributiepunten,
  altsienKernleden,
}: AfleverlocatieManagementProps) {
  const t = useTranslations("karTracker.afleverlocaties");
  const router = useRouter();

  const [afleverlocaties, setAfleverlocaties] = useState(initialAfleverlocaties);

  function zoneLabelFor(zoneId: number) {
    return zones.find((zone) => zone.id === zoneId)?.name ?? "";
  }

  function distributiepuntLabelFor(distributiepuntId: number) {
    return distributiepunten.find((item) => item.id === distributiepuntId)?.name ?? "";
  }

  function kernlidLabelFor(kernlidId: number | null) {
    if (kernlidId === null) return "";
    const kernlid = altsienKernleden.find((item) => item.id === kernlidId);
    return kernlid ? kernlidLabel(kernlid) : "";
  }

  function upsert(updated: KarTrackerAfleverlocatie) {
    setAfleverlocaties((current) => {
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
        <AfleverlocatieFormDialog
          trigger={<Button>{t("newAfleverlocatie")}</Button>}
          onSaved={upsert}
          zones={zones}
          distributiepunten={distributiepunten}
          altsienKernleden={altsienKernleden}
        />
      </div>

      <div className="rounded-md border [&>div]:max-h-[65vh] [&>div]:overflow-y-auto">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="sticky top-0 z-20 bg-background font-bold underline">{t("columnName")}</TableHead>
              <TableHead className="sticky top-0 z-20 bg-background font-bold underline">
                {t("columnDescription")}
              </TableHead>
              <TableHead className="sticky top-0 z-20 bg-background font-bold underline">{t("columnZone")}</TableHead>
              <TableHead className="sticky top-0 z-20 bg-background font-bold underline">
                {t("columnDistributiepunt")}
              </TableHead>
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
            {afleverlocaties.map((afleverlocatie) => (
              <TableRow key={afleverlocatie.id} className="group">
                <TableCell className="font-medium">{afleverlocatie.name}</TableCell>
                <TableCell className="text-muted-foreground">{afleverlocatie.description ?? ""}</TableCell>
                <TableCell className="text-muted-foreground">{zoneLabelFor(afleverlocatie.zone_id)}</TableCell>
                <TableCell className="text-muted-foreground">
                  {distributiepuntLabelFor(afleverlocatie.distributiepunt_id)}
                </TableCell>
                <TableCell className="text-muted-foreground">{afleverlocatie.latitude ?? ""}</TableCell>
                <TableCell className="text-muted-foreground">{afleverlocatie.longitude ?? ""}</TableCell>
                <TableCell className="text-muted-foreground">{afleverlocatie.terrein_positie ?? ""}</TableCell>
                <TableCell className="text-muted-foreground">
                  {kernlidLabelFor(afleverlocatie.altsien_kernlid_id)}
                </TableCell>
                <TableCell className="sticky right-0 z-10 bg-background group-hover:bg-muted/50">
                  <div className="flex justify-end gap-1">
                    <AfleverlocatieFormDialog
                      afleverlocatie={afleverlocatie}
                      trigger={
                        <Button variant="ghost" size="icon" aria-label={t("change")} title={t("change")}>
                          <Pencil className="size-4" />
                        </Button>
                      }
                      onSaved={upsert}
                      zones={zones}
                      distributiepunten={distributiepunten}
                      altsienKernleden={altsienKernleden}
                    />
                    <DeleteAfleverlocatieAlertDialog
                      afleverlocatie={afleverlocatie}
                      onDeleted={(id) => {
                        setAfleverlocaties((current) => current.filter((item) => item.id !== id));
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

interface AfleverlocatieFormDialogProps {
  afleverlocatie?: KarTrackerAfleverlocatie;
  trigger: React.ReactElement;
  onSaved: (afleverlocatie: KarTrackerAfleverlocatie) => void;
  zones: KarTrackerZone[];
  distributiepunten: KarTrackerDistributiepunt[];
  altsienKernleden: AltsienKernlid[];
}

function AfleverlocatieFormDialog({
  afleverlocatie,
  trigger,
  onSaved,
  zones,
  distributiepunten,
  altsienKernleden,
}: AfleverlocatieFormDialogProps) {
  const t = useTranslations("karTracker.afleverlocaties");
  const isEditing = afleverlocatie !== undefined;
  const [isOpen, setIsOpen] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [form, setForm] = useState<AfleverlocatieFormState>(
    afleverlocatie ? toFormValues(afleverlocatie) : EMPTY_FORM,
  );

  function handleOpenChange(open: boolean) {
    setIsOpen(open);
    if (open) {
      // Start from the delivery location's latest known values each time
      // the dialog is opened, in case they changed since last time.
      setForm(afleverlocatie ? toFormValues(afleverlocatie) : EMPTY_FORM);
    }
  }

  function updateField<K extends keyof AfleverlocatieFormState>(field: K, value: AfleverlocatieFormState[K]) {
    setForm((current) => ({ ...current, [field]: value }));
  }

  async function handleSubmit() {
    if (form.zone_id === null || form.distributiepunt_id === null) return;
    const payload: KarTrackerAfleverlocatieInput = { ...form, zone_id: form.zone_id, distributiepunt_id: form.distributiepunt_id };

    setIsSubmitting(true);
    try {
      const saved = isEditing
        ? await updateAfleverlocatie(afleverlocatie.id, payload)
        : await createAfleverlocatie(payload);
      toast.success(isEditing ? t("afleverlocatieUpdated") : t("afleverlocatieCreated"));
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
            <Label htmlFor="afleverlocatie-name">{t("nameLabel")}</Label>
            <Input
              id="afleverlocatie-name"
              value={form.name}
              onChange={(event) => updateField("name", event.target.value)}
            />
          </div>
          <div className="col-span-2 flex flex-col gap-2">
            <Label htmlFor="afleverlocatie-description">{t("descriptionLabel")}</Label>
            <Textarea
              id="afleverlocatie-description"
              value={form.description ?? ""}
              onChange={(event) => updateField("description", event.target.value || null)}
            />
          </div>
          <div className="flex flex-col gap-2">
            <Label htmlFor="afleverlocatie-zone">{t("zoneLabel")}</Label>
            <Select
              value={form.zone_id ? String(form.zone_id) : ""}
              onValueChange={(value) => updateField("zone_id", value ? Number(value) : null)}
            >
              <SelectTrigger id="afleverlocatie-zone">
                <SelectValue>{(value: string | null) => zones.find((zone) => String(zone.id) === value)?.name}</SelectValue>
              </SelectTrigger>
              <SelectContent>
                {zones.map((zone) => (
                  <SelectItem key={zone.id} value={String(zone.id)}>
                    {zone.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="flex flex-col gap-2">
            <Label htmlFor="afleverlocatie-distributiepunt">{t("distributiepuntLabel")}</Label>
            <Select
              value={form.distributiepunt_id ? String(form.distributiepunt_id) : ""}
              onValueChange={(value) => updateField("distributiepunt_id", value ? Number(value) : null)}
            >
              <SelectTrigger id="afleverlocatie-distributiepunt">
                <SelectValue>
                  {(value: string | null) => distributiepunten.find((item) => String(item.id) === value)?.name}
                </SelectValue>
              </SelectTrigger>
              <SelectContent>
                {distributiepunten.map((distributiepunt) => (
                  <SelectItem key={distributiepunt.id} value={String(distributiepunt.id)}>
                    {distributiepunt.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="flex flex-col gap-2">
            <Label htmlFor="afleverlocatie-latitude">{t("latitudeLabel")}</Label>
            <Input
              id="afleverlocatie-latitude"
              type="number"
              step="any"
              value={form.latitude ?? ""}
              onChange={(event) => updateField("latitude", event.target.value ? Number(event.target.value) : null)}
            />
          </div>
          <div className="flex flex-col gap-2">
            <Label htmlFor="afleverlocatie-longitude">{t("longitudeLabel")}</Label>
            <Input
              id="afleverlocatie-longitude"
              type="number"
              step="any"
              value={form.longitude ?? ""}
              onChange={(event) => updateField("longitude", event.target.value ? Number(event.target.value) : null)}
            />
          </div>
          <div className="flex flex-col gap-2">
            <Label htmlFor="afleverlocatie-terrein-positie">{t("terreinPositieLabel")}</Label>
            <Input
              id="afleverlocatie-terrein-positie"
              value={form.terrein_positie ?? ""}
              onChange={(event) => updateField("terrein_positie", event.target.value || null)}
            />
          </div>
          <div className="flex flex-col gap-2">
            <Label htmlFor="afleverlocatie-altsien-kernlid">{t("altsienKernlidLabel")}</Label>
            <Select
              value={form.altsien_kernlid_id ? String(form.altsien_kernlid_id) : NO_KERNLID_VALUE}
              onValueChange={(value) =>
                updateField("altsien_kernlid_id", value && value !== NO_KERNLID_VALUE ? Number(value) : null)
              }
            >
              <SelectTrigger id="afleverlocatie-altsien-kernlid">
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
          <Button
            onClick={handleSubmit}
            disabled={isSubmitting || !form.name.trim() || !form.zone_id || !form.distributiepunt_id}
          >
            {isEditing ? t("change") : t("newAfleverlocatie")}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

interface DeleteAfleverlocatieAlertDialogProps {
  afleverlocatie: KarTrackerAfleverlocatie;
  onDeleted: (afleverlocatieId: number) => void;
}

function DeleteAfleverlocatieAlertDialog({ afleverlocatie, onDeleted }: DeleteAfleverlocatieAlertDialogProps) {
  const t = useTranslations("karTracker.afleverlocaties");
  const tCommon = useTranslations("common");
  const [isOpen, setIsOpen] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);

  async function handleConfirmDelete() {
    setIsDeleting(true);
    try {
      await deleteAfleverlocatie(afleverlocatie.id);
      toast.success(t("afleverlocatieDeleted"));
      onDeleted(afleverlocatie.id);
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
          <AlertDialogDescription>{t("deleteConfirmDescription", { name: afleverlocatie.name })}</AlertDialogDescription>
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
