"use client";

// Intervention Requests' "Intervention Statuses" screen: a table of
// statuses with add/change/delete, following the same dialog/table pattern
// as intervention-requests-management.tsx's own RequestFormDialog. Used to
// be a thin wrapper around the shared LookupManagement component (see
// components/module-9/lookup-management.tsx), but that component is
// deliberately single-field and shared by several other lookup screens
// (Season, ProductType, ...) that must not gain these extra fields, so this
// screen now has its own bespoke form for its 3 fields: name, "open"
// checkbox, and colour.

import { useState } from "react";
import { Pencil, Trash2 } from "lucide-react";
import { useTranslations } from "next-intl";
import { toast } from "sonner";
import { useRouter } from "@/i18n/navigation";
import {
  ApiError,
  createInterventionStatus,
  deleteInterventionStatus,
  updateInterventionStatus,
} from "@/lib/api";
import type { InterventionStatus, InterventionStatusInput } from "@/lib/types";
import { STATUS_COLOR_INFO, STATUS_COLOR_KEYS, isStatusColorKey, type StatusColorKey } from "@/lib/status-colors";
import { cn } from "@/lib/utils";
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
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";

interface InterventionStatusManagementProps {
  initialStatuses: InterventionStatus[];
}

const EMPTY_FORM: InterventionStatusInput = { name: "", is_open: true, color: "gray" };

function toFormValues(item: InterventionStatus): InterventionStatusInput {
  return { name: item.name, is_open: item.is_open, color: item.color };
}

/** A small solid dot in the given palette colour, shown next to a colour's
 *  name both in the picker and in the table. */
function ColorSwatch({ color }: { color: string }) {
  const swatchClassName = isStatusColorKey(color) ? STATUS_COLOR_INFO[color].swatchClassName : "bg-muted";
  return <span className={cn("inline-block size-3 rounded-full", swatchClassName)} />;
}

export function InterventionStatusManagement({ initialStatuses }: InterventionStatusManagementProps) {
  const t = useTranslations("interventionRequests.status");
  const router = useRouter();

  const [statuses, setStatuses] = useState(initialStatuses);

  function colorNameFor(color: string) {
    return isStatusColorKey(color) ? t(`colorNames.${color}`) : color;
  }

  function upsert(updated: InterventionStatus) {
    setStatuses((current) => {
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
        <StatusFormDialog trigger={<Button>{t("newStatus")}</Button>} onSaved={upsert} />
      </div>

      <div className="overflow-x-auto rounded-md border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="font-bold underline">{t("tableName")}</TableHead>
              <TableHead className="font-bold underline">{t("columnIsOpen")}</TableHead>
              <TableHead className="font-bold underline">{t("columnColor")}</TableHead>
              <TableHead className="text-right font-bold underline">{t("tableActions")}</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {statuses.map((item) => (
              <TableRow key={item.id}>
                <TableCell className="font-medium">{item.name}</TableCell>
                <TableCell className="text-muted-foreground">{item.is_open ? t("openLabel") : t("closedLabel")}</TableCell>
                <TableCell>
                  <div className="flex items-center gap-2 text-muted-foreground">
                    <ColorSwatch color={item.color} />
                    {colorNameFor(item.color)}
                  </div>
                </TableCell>
                <TableCell>
                  <div className="flex justify-end gap-1">
                    <StatusFormDialog
                      item={item}
                      trigger={
                        <Button variant="ghost" size="icon" aria-label={t("change")} title={t("change")}>
                          <Pencil className="size-4" />
                        </Button>
                      }
                      onSaved={upsert}
                    />
                    <DeleteStatusAlertDialog
                      item={item}
                      onDeleted={(deletedId) => {
                        setStatuses((current) => current.filter((current_item) => current_item.id !== deletedId));
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

interface StatusFormDialogProps {
  item?: InterventionStatus;
  trigger: React.ReactElement;
  onSaved: (item: InterventionStatus) => void;
}

function StatusFormDialog({ item, trigger, onSaved }: StatusFormDialogProps) {
  const t = useTranslations("interventionRequests.status");
  const isEditing = item !== undefined;
  const [isOpen, setIsOpen] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [form, setForm] = useState<InterventionStatusInput>(item ? toFormValues(item) : EMPTY_FORM);

  function handleOpenChange(open: boolean) {
    setIsOpen(open);
    if (open) {
      // Start from the status's latest known values each time the dialog
      // is opened, in case they changed since last time.
      setForm(item ? toFormValues(item) : EMPTY_FORM);
    }
  }

  function updateField<K extends keyof InterventionStatusInput>(field: K, value: InterventionStatusInput[K]) {
    setForm((current) => ({ ...current, [field]: value }));
  }

  async function handleSubmit() {
    setIsSubmitting(true);
    try {
      const payload: InterventionStatusInput = { ...form, name: form.name.trim() };
      const savedItem = isEditing
        ? await updateInterventionStatus(item.id, payload)
        : await createInterventionStatus(payload);
      toast.success(isEditing ? t("statusUpdated") : t("statusCreated"));
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
            <Label htmlFor="status-name">{t("nameLabel")}</Label>
            <Input id="status-name" value={form.name} onChange={(event) => updateField("name", event.target.value)} />
          </div>

          <div className="flex items-center gap-2">
            <Checkbox
              id="status-is-open"
              checked={form.is_open}
              onCheckedChange={(checked) => updateField("is_open", checked === true)}
            />
            <Label htmlFor="status-is-open">{t("isOpenLabel")}</Label>
          </div>

          <div className="flex flex-col gap-2">
            <Label htmlFor="status-color">{t("colorLabel")}</Label>
            <Select value={form.color} onValueChange={(value) => updateField("color", value ?? "gray")}>
              <SelectTrigger id="status-color">
                <SelectValue>
                  {(value: string | null) =>
                    value ? (
                      <span className="flex items-center gap-2">
                        <ColorSwatch color={value} />
                        {isStatusColorKey(value) ? t(`colorNames.${value}`) : value}
                      </span>
                    ) : (
                      ""
                    )
                  }
                </SelectValue>
              </SelectTrigger>
              <SelectContent>
                {STATUS_COLOR_KEYS.map((key: StatusColorKey) => (
                  <SelectItem key={key} value={key}>
                    <span className="flex items-center gap-2">
                      <ColorSwatch color={key} />
                      {t(`colorNames.${key}`)}
                    </span>
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>

        <DialogFooter>
          <Button onClick={handleSubmit} disabled={isSubmitting || !form.name.trim()}>
            {isEditing ? t("change") : t("newStatus")}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

interface DeleteStatusAlertDialogProps {
  item: InterventionStatus;
  onDeleted: (itemId: number) => void;
}

function DeleteStatusAlertDialog({ item, onDeleted }: DeleteStatusAlertDialogProps) {
  const t = useTranslations("interventionRequests.status");
  const tCommon = useTranslations("common");
  const [isOpen, setIsOpen] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);

  async function handleConfirmDelete() {
    setIsDeleting(true);
    try {
      await deleteInterventionStatus(item.id);
      toast.success(t("statusDeleted"));
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
