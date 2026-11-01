"use client";

// Atelier's "Masterdata > Retourstatussen" screen: what can be wrong with a
// returned piece ("Beschadigd", "Zeer vuil", ...). The desk picks one per piece
// on Terugbrengen. A status already used can only be deactivated; buttons only
// appear for the rights the user has (the backend checks too).

import { useState } from "react";
import { Pencil, Trash2 } from "lucide-react";
import { useTranslations } from "next-intl";
import { toast } from "sonner";
import { useRouter } from "@/i18n/navigation";
import { ApiError, createAtelierReturnStatus, deleteAtelierReturnStatus, updateAtelierReturnStatus } from "@/lib/api";
import type { AtelierReturnStatus, AtelierReturnStatusInput } from "@/lib/types";
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
import { Badge } from "@/components/ui/badge";
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

const EMPTY_FORM: AtelierReturnStatusInput = { name: "", active: true };

/** The statuses by name, as the backend sends them. */
function sortByName(statuses: AtelierReturnStatus[]) {
  return [...statuses].sort((a, b) => a.name.localeCompare(b.name));
}

interface ReturnStatusManagementProps {
  initialStatuses: AtelierReturnStatus[];
  canCreate: boolean;
  canEdit: boolean;
  canDelete: boolean;
}

export function ReturnStatusManagement({ initialStatuses, canCreate, canEdit, canDelete }: ReturnStatusManagementProps) {
  const t = useTranslations("atelier.returnStatuses");
  const router = useRouter();

  // Kept in local state so changes show instantly, without a page reload.
  const [statuses, setStatuses] = useState(initialStatuses);

  function upsert(saved: AtelierReturnStatus) {
    setStatuses((current) => sortByName([...current.filter((item) => item.id !== saved.id), saved]));
    router.refresh();
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight underline">{t("title")}</h1>
          <p className="text-muted-foreground">{t("description")}</p>
        </div>
        {canCreate && <ReturnStatusFormDialog trigger={<Button>{t("newStatus")}</Button>} onSaved={upsert} />}
      </div>

      <div className="rounded-md border [&>div]:max-h-[65vh] [&>div]:overflow-y-auto">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="sticky top-0 z-20 bg-background font-bold underline">{t("columnName")}</TableHead>
              <TableHead className="sticky top-0 z-20 bg-background font-bold underline">{t("columnActive")}</TableHead>
              <TableHead className="sticky top-0 right-0 z-30 bg-background text-right font-bold underline">
                {t("tableActions")}
              </TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {statuses.length === 0 && (
              <TableRow>
                <TableCell colSpan={3} className="text-center text-muted-foreground">
                  {t("empty")}
                </TableCell>
              </TableRow>
            )}
            {statuses.map((status) => (
              <TableRow key={status.id} className="group">
                <TableCell className="font-medium">{status.name}</TableCell>
                <TableCell>
                  {status.active ? t("activeYes") : <Badge variant="secondary">{t("activeNo")}</Badge>}
                </TableCell>
                <TableCell className="sticky right-0 z-10 bg-background group-hover:bg-muted/50">
                  <div className="flex justify-end gap-1">
                    {canEdit && (
                      <ReturnStatusFormDialog
                        status={status}
                        trigger={
                          <Button variant="ghost" size="icon" aria-label={t("change")} title={t("change")}>
                            <Pencil className="size-4" />
                          </Button>
                        }
                        onSaved={upsert}
                      />
                    )}
                    {canDelete && (
                      <DeleteReturnStatusDialog
                        status={status}
                        onDeleted={(statusId) => {
                          setStatuses((current) => current.filter((item) => item.id !== statusId));
                          router.refresh();
                        }}
                      />
                    )}
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

interface ReturnStatusFormDialogProps {
  status?: AtelierReturnStatus;
  trigger: React.ReactElement;
  onSaved: (status: AtelierReturnStatus) => void;
}

function ReturnStatusFormDialog({ status, trigger, onSaved }: ReturnStatusFormDialogProps) {
  const t = useTranslations("atelier.returnStatuses");
  const isEditing = status !== undefined;
  const [isOpen, setIsOpen] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [form, setForm] = useState<AtelierReturnStatusInput>(EMPTY_FORM);

  function handleOpenChange(open: boolean) {
    setIsOpen(open);
    if (open) {
      // Start from the status's latest values every time the dialog opens.
      setForm(status ? { name: status.name, active: status.active } : EMPTY_FORM);
    }
  }

  async function handleSubmit() {
    setIsSubmitting(true);
    try {
      const payload = { ...form, name: form.name.trim() };
      const saved = isEditing ? await updateAtelierReturnStatus(status.id, payload) : await createAtelierReturnStatus(payload);
      toast.success(isEditing ? t("statusUpdated") : t("statusCreated"));
      onSaved(saved);
      setIsOpen(false);
    } catch (error) {
      toast.error(error instanceof ApiError ? error.message : t("saveFailed"));
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
          <DialogDescription>{t("formDescription")}</DialogDescription>
        </DialogHeader>

        <div className="flex flex-col gap-4">
          <div className="flex flex-col gap-2">
            <Label htmlFor="atelier-return-status-name">
              {t("nameLabel")} <span aria-hidden="true" className="text-destructive">*</span>
            </Label>
            <Input
              id="atelier-return-status-name"
              value={form.name}
              maxLength={100}
              onChange={(event) => setForm((current) => ({ ...current, name: event.target.value }))}
            />
          </div>
          <div className="flex items-center gap-2">
            <Checkbox
              id="atelier-return-status-active"
              checked={form.active}
              onCheckedChange={(checked) => setForm((current) => ({ ...current, active: checked === true }))}
            />
            <Label htmlFor="atelier-return-status-active">{t("activeLabel")}</Label>
          </div>
        </div>

        <DialogFooter>
          <Button onClick={handleSubmit} disabled={isSubmitting || !form.name.trim()}>
            {t("save")}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

interface DeleteReturnStatusDialogProps {
  status: AtelierReturnStatus;
  onDeleted: (statusId: number) => void;
}

function DeleteReturnStatusDialog({ status, onDeleted }: DeleteReturnStatusDialogProps) {
  const t = useTranslations("atelier.returnStatuses");
  const tCommon = useTranslations("common");
  const [isOpen, setIsOpen] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);

  async function handleConfirmDelete() {
    setIsDeleting(true);
    try {
      await deleteAtelierReturnStatus(status.id);
      toast.success(t("statusDeleted"));
      onDeleted(status.id);
      setIsOpen(false);
    } catch (error) {
      toast.error(error instanceof ApiError ? error.message : t("deleteFailed"));
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
          <AlertDialogDescription>{t("deleteConfirmDescription", { name: status.name })}</AlertDialogDescription>
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
