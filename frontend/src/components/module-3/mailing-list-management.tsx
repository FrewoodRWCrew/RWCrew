"use client";

// Intervention Requests' "Mailing List" settings screen: a table of email
// addresses with add/change/delete. Every *active* address here gets an
// email (with the delivery-note PDF attached) as soon as a new intervention
// request arrives — from the staff screen, the public QR form or the phone
// app (see backend app/modules/module_3/notifications.py). Same dialog/
// table pattern as intervention-status-management.tsx.

import { useState } from "react";
import { Pencil, Trash2 } from "lucide-react";
import { useTranslations } from "next-intl";
import { toast } from "sonner";
import { useRouter } from "@/i18n/navigation";
import { ApiError, createMailingRecipient, deleteMailingRecipient, updateMailingRecipient } from "@/lib/api";
import type { MailingRecipient, MailingRecipientInput } from "@/lib/types";
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

interface MailingListManagementProps {
  initialRecipients: MailingRecipient[];
}

const EMPTY_FORM: MailingRecipientInput = { email: "", name: null, is_active: true };

// A deliberately loose check, only to keep the save button disabled for
// obvious typos — the backend does the real email validation.
const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

function toFormValues(item: MailingRecipient): MailingRecipientInput {
  return { email: item.email, name: item.name, is_active: item.is_active };
}

export function MailingListManagement({ initialRecipients }: MailingListManagementProps) {
  const t = useTranslations("interventionRequests.mailingList");
  const router = useRouter();

  const [recipients, setRecipients] = useState(initialRecipients);

  // Insert or replace a saved row, keeping the list sorted by address
  // (the same order the backend returns).
  function upsert(updated: MailingRecipient) {
    setRecipients((current) => {
      const exists = current.some((item) => item.id === updated.id);
      const next = exists ? current.map((item) => (item.id === updated.id ? updated : item)) : [...current, updated];
      return next.sort((a, b) => a.email.localeCompare(b.email));
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
        <RecipientFormDialog trigger={<Button>{t("newRecipient")}</Button>} onSaved={upsert} />
      </div>

      {/* Scrolls inside a capped box with pinned header + Actions column. */}
      <div className="rounded-md border [&>div]:max-h-[65vh] [&>div]:overflow-y-auto">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="sticky top-0 z-20 bg-background font-bold underline">{t("columnEmail")}</TableHead>
              <TableHead className="sticky top-0 z-20 bg-background font-bold underline">{t("columnName")}</TableHead>
              <TableHead className="sticky top-0 z-20 bg-background font-bold underline">{t("columnActive")}</TableHead>
              <TableHead className="sticky top-0 right-0 z-30 bg-background text-right font-bold underline">
                {t("tableActions")}
              </TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {recipients.length === 0 && (
              <TableRow>
                <TableCell colSpan={4} className="text-center text-muted-foreground">
                  {t("empty")}
                </TableCell>
              </TableRow>
            )}
            {recipients.map((item) => (
              <TableRow key={item.id} className="group">
                <TableCell className="font-medium">{item.email}</TableCell>
                <TableCell className="text-muted-foreground">{item.name ?? ""}</TableCell>
                <TableCell className="text-muted-foreground">
                  {item.is_active ? t("activeLabel") : t("pausedLabel")}
                </TableCell>
                <TableCell className="sticky right-0 z-10 bg-background group-hover:bg-muted/50">
                  <div className="flex justify-end gap-1">
                    <RecipientFormDialog
                      item={item}
                      trigger={
                        <Button variant="ghost" size="icon" aria-label={t("change")} title={t("change")}>
                          <Pencil className="size-4" />
                        </Button>
                      }
                      onSaved={upsert}
                    />
                    <DeleteRecipientAlertDialog
                      item={item}
                      onDeleted={(deletedId) => {
                        setRecipients((current) => current.filter((row) => row.id !== deletedId));
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

interface RecipientFormDialogProps {
  item?: MailingRecipient;
  trigger: React.ReactElement;
  onSaved: (item: MailingRecipient) => void;
}

function RecipientFormDialog({ item, trigger, onSaved }: RecipientFormDialogProps) {
  const t = useTranslations("interventionRequests.mailingList");
  const isEditing = item !== undefined;
  const [isOpen, setIsOpen] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [form, setForm] = useState<MailingRecipientInput>(item ? toFormValues(item) : EMPTY_FORM);

  function handleOpenChange(open: boolean) {
    setIsOpen(open);
    if (open) {
      // Start from the row's latest known values each time the dialog opens.
      setForm(item ? toFormValues(item) : EMPTY_FORM);
    }
  }

  function updateField<K extends keyof MailingRecipientInput>(field: K, value: MailingRecipientInput[K]) {
    setForm((current) => ({ ...current, [field]: value }));
  }

  const isEmailValid = EMAIL_PATTERN.test(form.email.trim());

  async function handleSubmit() {
    setIsSubmitting(true);
    try {
      // Blank name → no name; the backend lower-cases the address.
      const payload: MailingRecipientInput = {
        ...form,
        email: form.email.trim(),
        name: form.name?.trim() ? form.name.trim() : null,
      };
      const savedItem = isEditing
        ? await updateMailingRecipient(item.id, payload)
        : await createMailingRecipient(payload);
      toast.success(isEditing ? t("recipientUpdated") : t("recipientCreated"));
      onSaved(savedItem);
      setIsOpen(false);
    } catch (error) {
      // 409 = already on the list: show our own translated message.
      const message =
        error instanceof ApiError && error.status === 409
          ? t("duplicate")
          : error instanceof ApiError
            ? error.message
            : isEditing
              ? t("updateFailed")
              : t("createFailed");
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
            <Label htmlFor="recipient-email">{t("emailLabel")}</Label>
            <Input
              id="recipient-email"
              type="email"
              autoComplete="off"
              value={form.email}
              onChange={(event) => updateField("email", event.target.value)}
            />
          </div>

          <div className="flex flex-col gap-2">
            <Label htmlFor="recipient-name">{t("nameLabel")}</Label>
            <Input
              id="recipient-name"
              value={form.name ?? ""}
              onChange={(event) => updateField("name", event.target.value)}
            />
          </div>

          <div className="flex items-center gap-2">
            <Checkbox
              id="recipient-active"
              checked={form.is_active}
              onCheckedChange={(checked) => updateField("is_active", checked === true)}
            />
            <Label htmlFor="recipient-active">{t("activeCheckboxLabel")}</Label>
          </div>
        </div>

        <DialogFooter>
          <Button onClick={handleSubmit} disabled={isSubmitting || !isEmailValid}>
            {isEditing ? t("change") : t("newRecipient")}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

interface DeleteRecipientAlertDialogProps {
  item: MailingRecipient;
  onDeleted: (itemId: number) => void;
}

function DeleteRecipientAlertDialog({ item, onDeleted }: DeleteRecipientAlertDialogProps) {
  const t = useTranslations("interventionRequests.mailingList");
  const tCommon = useTranslations("common");
  const [isOpen, setIsOpen] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);

  async function handleConfirmDelete() {
    setIsDeleting(true);
    try {
      await deleteMailingRecipient(item.id);
      toast.success(t("recipientDeleted"));
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
          <AlertDialogDescription>{t("deleteConfirmDescription", { email: item.email })}</AlertDialogDescription>
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
