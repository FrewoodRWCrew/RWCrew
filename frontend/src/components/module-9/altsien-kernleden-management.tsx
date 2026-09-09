"use client";

// MasterData's "Altsien Kernleden" screen: a table of contacts with
// add/change/delete, following the same dialog/table pattern as
// products-management.tsx/festival-management.tsx — a bespoke component
// (not the shared LookupManagement) since this entity has four fields,
// not one.

import { useState } from "react";
import { Pencil, Trash2 } from "lucide-react";
import { useTranslations } from "next-intl";
import { toast } from "sonner";
import { useRouter } from "@/i18n/navigation";
import { ApiError, createAltsienKernlid, deleteAltsienKernlid, updateAltsienKernlid } from "@/lib/api";
import type { AltsienKernlid, AltsienKernlidInput } from "@/lib/types";
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
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";

interface AltsienKernledenManagementProps {
  initialAltsienKernleden: AltsienKernlid[];
}

const EMPTY_FORM: AltsienKernlidInput = {
  first_name: "",
  name: "",
  telephone_number: "",
  email: "",
};

function toFormValues(contact: AltsienKernlid): AltsienKernlidInput {
  return {
    first_name: contact.first_name,
    name: contact.name,
    telephone_number: contact.telephone_number,
    email: contact.email,
  };
}

export function AltsienKernledenManagement({ initialAltsienKernleden }: AltsienKernledenManagementProps) {
  const t = useTranslations("masterdata.altsienKernleden");
  const router = useRouter();

  const [contacts, setContacts] = useState(initialAltsienKernleden);

  function upsert(updated: AltsienKernlid) {
    setContacts((current) => {
      const exists = current.some((contact) => contact.id === updated.id);
      return exists
        ? current.map((contact) => (contact.id === updated.id ? updated : contact))
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
        <AltsienKernlidFormDialog trigger={<Button>{t("newContact")}</Button>} onSaved={upsert} />
      </div>

      <div className="rounded-md border [&>div]:max-h-[65vh] [&>div]:overflow-y-auto">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="sticky top-0 z-20 bg-background font-bold underline">{t("columnFirstName")}</TableHead>
              <TableHead className="sticky top-0 z-20 bg-background font-bold underline">{t("columnName")}</TableHead>
              <TableHead className="sticky top-0 z-20 bg-background font-bold underline">{t("columnTelephoneNumber")}</TableHead>
              <TableHead className="sticky top-0 z-20 bg-background font-bold underline">{t("columnEmail")}</TableHead>
              <TableHead className="sticky top-0 right-0 z-30 bg-background text-right font-bold underline">
                {t("tableActions")}
              </TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {contacts.map((contact) => (
              <TableRow key={contact.id} className="group">
                <TableCell className="font-medium">{contact.first_name}</TableCell>
                <TableCell className="font-medium">{contact.name}</TableCell>
                <TableCell className="text-muted-foreground">{contact.telephone_number}</TableCell>
                <TableCell className="text-muted-foreground">{contact.email}</TableCell>
                <TableCell className="sticky right-0 z-10 bg-background group-hover:bg-muted/50">
                  <div className="flex justify-end gap-1">
                    <AltsienKernlidFormDialog
                      contact={contact}
                      trigger={
                        <Button variant="ghost" size="icon" aria-label={t("change")} title={t("change")}>
                          <Pencil className="size-4" />
                        </Button>
                      }
                      onSaved={upsert}
                    />
                    <DeleteAltsienKernlidAlertDialog
                      contact={contact}
                      onDeleted={(contactId) => {
                        setContacts((current) => current.filter((item) => item.id !== contactId));
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

interface AltsienKernlidFormDialogProps {
  contact?: AltsienKernlid;
  trigger: React.ReactElement;
  onSaved: (contact: AltsienKernlid) => void;
}

function AltsienKernlidFormDialog({ contact, trigger, onSaved }: AltsienKernlidFormDialogProps) {
  const t = useTranslations("masterdata.altsienKernleden");
  const isEditing = contact !== undefined;
  const [isOpen, setIsOpen] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [form, setForm] = useState<AltsienKernlidInput>(contact ? toFormValues(contact) : EMPTY_FORM);

  function handleOpenChange(open: boolean) {
    setIsOpen(open);
    if (open) {
      // Start from the contact's latest known values each time the
      // dialog is opened, in case they changed since last time.
      setForm(contact ? toFormValues(contact) : EMPTY_FORM);
    }
  }

  function updateField<K extends keyof AltsienKernlidInput>(field: K, value: AltsienKernlidInput[K]) {
    setForm((current) => ({ ...current, [field]: value }));
  }

  async function handleSubmit() {
    setIsSubmitting(true);
    try {
      const savedContact = isEditing ? await updateAltsienKernlid(contact.id, form) : await createAltsienKernlid(form);
      toast.success(isEditing ? t("contactUpdated") : t("contactCreated"));
      onSaved(savedContact);
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
          <div className="flex flex-col gap-2">
            <Label htmlFor="altsien-kernlid-first-name">{t("firstNameLabel")}</Label>
            <Input
              id="altsien-kernlid-first-name"
              value={form.first_name}
              onChange={(event) => updateField("first_name", event.target.value)}
            />
          </div>
          <div className="flex flex-col gap-2">
            <Label htmlFor="altsien-kernlid-name">{t("nameLabel")}</Label>
            <Input
              id="altsien-kernlid-name"
              value={form.name}
              onChange={(event) => updateField("name", event.target.value)}
            />
          </div>
          <div className="flex flex-col gap-2">
            <Label htmlFor="altsien-kernlid-telephone">{t("telephoneNumberLabel")}</Label>
            <Input
              id="altsien-kernlid-telephone"
              value={form.telephone_number}
              onChange={(event) => updateField("telephone_number", event.target.value)}
            />
          </div>
          <div className="flex flex-col gap-2">
            <Label htmlFor="altsien-kernlid-email">{t("emailLabel")}</Label>
            <Input
              id="altsien-kernlid-email"
              type="email"
              value={form.email}
              onChange={(event) => updateField("email", event.target.value)}
            />
          </div>
        </div>

        <DialogFooter>
          <Button
            onClick={handleSubmit}
            disabled={isSubmitting || !form.first_name || !form.name || !form.telephone_number || !form.email}
          >
            {isEditing ? t("change") : t("newContact")}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

interface DeleteAltsienKernlidAlertDialogProps {
  contact: AltsienKernlid;
  onDeleted: (contactId: number) => void;
}

function DeleteAltsienKernlidAlertDialog({ contact, onDeleted }: DeleteAltsienKernlidAlertDialogProps) {
  const t = useTranslations("masterdata.altsienKernleden");
  const tCommon = useTranslations("common");
  const [isOpen, setIsOpen] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);

  async function handleConfirmDelete() {
    setIsDeleting(true);
    try {
      await deleteAltsienKernlid(contact.id);
      toast.success(t("contactDeleted"));
      onDeleted(contact.id);
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
          <AlertDialogDescription>
            {t("deleteConfirmDescription", { name: `${contact.first_name} ${contact.name}` })}
          </AlertDialogDescription>
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
