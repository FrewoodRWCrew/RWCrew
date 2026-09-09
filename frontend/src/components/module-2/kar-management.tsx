"use client";

// KarTracker's "KarManagement" screen: the fleet registry itself — a table
// of karren (physical carts) with add/change/delete. Modeled on
// MasterData's FestivalManagement (a bespoke, multi-field CRUD screen),
// since KarManagement has too many fields for the shared LookupManagement
// component. Status is picked from the KarStatussen lookup screen;
// TransportType and Team ("Ploeg") are picked from module-9's existing
// Products/Teams master data (cross-module, per how this module's
// Masterdata phase was designed).

import { useState } from "react";
import { Pencil, Trash2 } from "lucide-react";
import { useTranslations } from "next-intl";
import { toast } from "sonner";
import { useRouter } from "@/i18n/navigation";
import { ApiError, createKar, deleteKar, updateKar } from "@/lib/api";
import type { KarTrackerKar, KarTrackerKarInput, KarTrackerKarStatus, Product, Team } from "@/lib/types";
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

interface KarManagementProps {
  initialKarren: KarTrackerKar[];
  karStatuses: KarTrackerKarStatus[];
  products: Product[];
  teams: Team[];
}

// Base UI's Select needs every item to have a non-empty value, so "no
// team assigned" (team_id is optional) is represented by this sentinel
// string instead of "".
const NO_TEAM_VALUE = "none";

// The form's own shape allows status_id/transport_type_id to be null while
// the user hasn't picked one yet — KarTrackerKarInput itself keeps them
// required, since that's the actual wire contract sent to the backend.
interface KarFormState extends Omit<KarTrackerKarInput, "status_id" | "transport_type_id"> {
  status_id: number | null;
  transport_type_id: number | null;
}

const EMPTY_FORM: KarFormState = {
  kar_nummer: "",
  status_id: null,
  team_id: null,
  transport_type_id: null,
  last_latitude: null,
  last_longitude: null,
  last_recorded_at: null,
};

function toFormValues(kar: KarTrackerKar): KarFormState {
  return {
    kar_nummer: kar.kar_nummer,
    status_id: kar.status_id,
    team_id: kar.team_id,
    transport_type_id: kar.transport_type_id,
    last_latitude: kar.last_latitude,
    last_longitude: kar.last_longitude,
    last_recorded_at: kar.last_recorded_at,
  };
}

// ISO datetimes from the backend are longer than the "YYYY-MM-DDTHH:mm"
// shape an <input type="datetime-local"> needs — trim to that.
function toDatetimeLocalValue(value: string | null): string {
  return value ? value.slice(0, 16) : "";
}

export function KarManagement({ initialKarren, karStatuses, products, teams }: KarManagementProps) {
  const t = useTranslations("karTracker.karManagement");
  const router = useRouter();

  const [karren, setKarren] = useState(initialKarren);

  function statusLabelFor(statusId: number) {
    return karStatuses.find((karStatus) => karStatus.id === statusId)?.name ?? "";
  }

  function transportTypeLabelFor(productId: number) {
    return products.find((product) => product.id === productId)?.name ?? "";
  }

  function teamLabelFor(teamId: number | null) {
    if (teamId === null) return "";
    return teams.find((team) => team.id === teamId)?.name ?? "";
  }

  function upsert(updated: KarTrackerKar) {
    setKarren((current) => {
      const exists = current.some((kar) => kar.id === updated.id);
      return exists
        ? current.map((kar) => (kar.id === updated.id ? updated : kar))
        : [...current, updated].sort((a, b) => a.kar_nummer.localeCompare(b.kar_nummer));
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
        <KarFormDialog
          trigger={<Button>{t("newKar")}</Button>}
          onSaved={upsert}
          karStatuses={karStatuses}
          products={products}
          teams={teams}
        />
      </div>

      <div className="rounded-md border [&>div]:max-h-[65vh] [&>div]:overflow-y-auto">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="sticky top-0 z-20 bg-background font-bold underline">{t("columnKarNummer")}</TableHead>
              <TableHead className="sticky top-0 z-20 bg-background font-bold underline">{t("columnStatus")}</TableHead>
              <TableHead className="sticky top-0 z-20 bg-background font-bold underline">{t("columnTeam")}</TableHead>
              <TableHead className="sticky top-0 z-20 bg-background font-bold underline">{t("columnTransportType")}</TableHead>
              <TableHead className="sticky top-0 z-20 bg-background font-bold underline">{t("columnLatitude")}</TableHead>
              <TableHead className="sticky top-0 z-20 bg-background font-bold underline">{t("columnLongitude")}</TableHead>
              <TableHead className="sticky top-0 z-20 bg-background font-bold underline">{t("columnLastRecordedAt")}</TableHead>
              <TableHead className="sticky top-0 right-0 z-30 bg-background text-right font-bold underline">
                {t("tableActions")}
              </TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {karren.map((kar) => (
              <TableRow key={kar.id} className="group">
                <TableCell className="font-medium">{kar.kar_nummer}</TableCell>
                <TableCell className="text-muted-foreground">{statusLabelFor(kar.status_id)}</TableCell>
                <TableCell className="text-muted-foreground">{teamLabelFor(kar.team_id)}</TableCell>
                <TableCell className="text-muted-foreground">{transportTypeLabelFor(kar.transport_type_id)}</TableCell>
                <TableCell className="text-muted-foreground">{kar.last_latitude ?? ""}</TableCell>
                <TableCell className="text-muted-foreground">{kar.last_longitude ?? ""}</TableCell>
                <TableCell className="text-muted-foreground">{toDatetimeLocalValue(kar.last_recorded_at)}</TableCell>
                <TableCell className="sticky right-0 z-10 bg-background group-hover:bg-muted/50">
                  <div className="flex justify-end gap-1">
                    <KarFormDialog
                      kar={kar}
                      trigger={
                        <Button variant="ghost" size="icon" aria-label={t("change")} title={t("change")}>
                          <Pencil className="size-4" />
                        </Button>
                      }
                      onSaved={upsert}
                      karStatuses={karStatuses}
                      products={products}
                      teams={teams}
                    />
                    <DeleteKarAlertDialog
                      kar={kar}
                      onDeleted={(karId) => {
                        setKarren((current) => current.filter((item) => item.id !== karId));
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

interface KarFormDialogProps {
  kar?: KarTrackerKar;
  trigger: React.ReactElement;
  onSaved: (kar: KarTrackerKar) => void;
  karStatuses: KarTrackerKarStatus[];
  products: Product[];
  teams: Team[];
}

function KarFormDialog({ kar, trigger, onSaved, karStatuses, products, teams }: KarFormDialogProps) {
  const t = useTranslations("karTracker.karManagement");
  const isEditing = kar !== undefined;
  const [isOpen, setIsOpen] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [form, setForm] = useState<KarFormState>(kar ? toFormValues(kar) : EMPTY_FORM);

  function handleOpenChange(open: boolean) {
    setIsOpen(open);
    if (open) {
      // Start from the kar's latest known values each time the dialog is
      // opened, in case they changed since last time.
      setForm(kar ? toFormValues(kar) : EMPTY_FORM);
    }
  }

  function updateField<K extends keyof KarFormState>(field: K, value: KarFormState[K]) {
    setForm((current) => ({ ...current, [field]: value }));
  }

  async function handleSubmit() {
    if (form.status_id === null || form.transport_type_id === null) return;
    const payload: KarTrackerKarInput = { ...form, status_id: form.status_id, transport_type_id: form.transport_type_id };

    setIsSubmitting(true);
    try {
      const savedKar = isEditing ? await updateKar(kar.id, payload) : await createKar(payload);
      toast.success(isEditing ? t("karUpdated") : t("karCreated"));
      onSaved(savedKar);
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
            <Label htmlFor="kar-nummer">{t("karNummerLabel")}</Label>
            <Input
              id="kar-nummer"
              value={form.kar_nummer}
              onChange={(event) => updateField("kar_nummer", event.target.value)}
            />
          </div>
          <div className="flex flex-col gap-2">
            <Label htmlFor="kar-status">{t("statusLabel")}</Label>
            <Select
              value={form.status_id ? String(form.status_id) : ""}
              onValueChange={(value) => updateField("status_id", value ? Number(value) : null)}
            >
              <SelectTrigger id="kar-status">
                <SelectValue>
                  {(value: string | null) => karStatuses.find((karStatus) => String(karStatus.id) === value)?.name}
                </SelectValue>
              </SelectTrigger>
              <SelectContent>
                {karStatuses.map((karStatus) => (
                  <SelectItem key={karStatus.id} value={String(karStatus.id)}>
                    {karStatus.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="flex flex-col gap-2">
            <Label htmlFor="kar-transport-type">{t("transportTypeLabel")}</Label>
            <Select
              value={form.transport_type_id ? String(form.transport_type_id) : ""}
              onValueChange={(value) => updateField("transport_type_id", value ? Number(value) : null)}
            >
              <SelectTrigger id="kar-transport-type">
                <SelectValue>{(value: string | null) => products.find((product) => String(product.id) === value)?.name}</SelectValue>
              </SelectTrigger>
              <SelectContent>
                {products.map((product) => (
                  <SelectItem key={product.id} value={String(product.id)}>
                    {product.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="col-span-2 flex flex-col gap-2">
            <Label htmlFor="kar-team">{t("teamLabel")}</Label>
            <Select
              value={form.team_id ? String(form.team_id) : NO_TEAM_VALUE}
              onValueChange={(value) =>
                updateField("team_id", value && value !== NO_TEAM_VALUE ? Number(value) : null)
              }
            >
              <SelectTrigger id="kar-team">
                <SelectValue>
                  {(value: string | null) =>
                    teams.find((team) => String(team.id) === value)?.name ?? t("noTeam")
                  }
                </SelectValue>
              </SelectTrigger>
              <SelectContent>
                <SelectItem value={NO_TEAM_VALUE}>{t("noTeam")}</SelectItem>
                {teams.map((team) => (
                  <SelectItem key={team.id} value={String(team.id)}>
                    {team.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="flex flex-col gap-2">
            <Label htmlFor="kar-latitude">{t("latitudeLabel")}</Label>
            <Input
              id="kar-latitude"
              type="number"
              step="any"
              value={form.last_latitude ?? ""}
              onChange={(event) => updateField("last_latitude", event.target.value ? Number(event.target.value) : null)}
            />
          </div>
          <div className="flex flex-col gap-2">
            <Label htmlFor="kar-longitude">{t("longitudeLabel")}</Label>
            <Input
              id="kar-longitude"
              type="number"
              step="any"
              value={form.last_longitude ?? ""}
              onChange={(event) => updateField("last_longitude", event.target.value ? Number(event.target.value) : null)}
            />
          </div>
          <div className="col-span-2 flex flex-col gap-2">
            <Label htmlFor="kar-last-recorded-at">{t("lastRecordedAtLabel")}</Label>
            <Input
              id="kar-last-recorded-at"
              type="datetime-local"
              value={toDatetimeLocalValue(form.last_recorded_at)}
              onChange={(event) => updateField("last_recorded_at", event.target.value || null)}
            />
          </div>
        </div>

        <DialogFooter>
          <Button
            onClick={handleSubmit}
            disabled={isSubmitting || !form.kar_nummer.trim() || !form.status_id || !form.transport_type_id}
          >
            {isEditing ? t("change") : t("newKar")}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

interface DeleteKarAlertDialogProps {
  kar: KarTrackerKar;
  onDeleted: (karId: number) => void;
}

function DeleteKarAlertDialog({ kar, onDeleted }: DeleteKarAlertDialogProps) {
  const t = useTranslations("karTracker.karManagement");
  const tCommon = useTranslations("common");
  const [isOpen, setIsOpen] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);

  async function handleConfirmDelete() {
    setIsDeleting(true);
    try {
      await deleteKar(kar.id);
      toast.success(t("karDeleted"));
      onDeleted(kar.id);
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
          <AlertDialogDescription>{t("deleteConfirmDescription", { name: kar.kar_nummer })}</AlertDialogDescription>
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
