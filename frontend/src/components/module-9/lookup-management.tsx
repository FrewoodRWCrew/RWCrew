"use client";

// The shared table + create/change/delete-dialog UI for MasterData's five
// simple "id + unique name" lookup screens (Seasons, and the four
// Products "selection criteria" lists: Type, Magazijnen, Categorieën,
// Limieten). Each screen's own *-management.tsx file is now a thin
// wrapper that supplies its translated labels and its api.ts
// create/update/delete functions as props — this file has no
// translation-key or endpoint knowledge of its own, so it never needs to
// change when a 6th lookup screen is added; only a new thin wrapper does.

import { useState } from "react";
import { Pencil, Trash2 } from "lucide-react";
import { toast } from "sonner";
import { useRouter } from "@/i18n/navigation";
import { ApiError } from "@/lib/api";
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

/** The shape every lookup entity has: a bare id + unique name. */
export interface LookupItem {
  id: number;
  name: string;
}

/** Every piece of already-translated text the shared UI needs, supplied
 * by each wrapper from its own next-intl namespace — this component
 * itself never calls useTranslations(), so it stays entity-agnostic.
 */
export interface LookupManagementLabels {
  title: string;
  description: string;
  tableName: string;
  tableActions: string;
  newItem: string;
  nameLabel: string;
  createTitle: string;
  createDescription: string;
  itemCreated: string;
  createFailed: string;
  change: string;
  delete: string;
  changeTitle: string;
  changeDescription: string;
  itemUpdated: string;
  updateFailed: string;
  deleteConfirmTitle: string;
  deleteConfirmDescription: (name: string) => string;
  itemDeleted: string;
  deleteFailed: string;
  cancel: string;
}

interface LookupManagementProps<T extends LookupItem> {
  initialItems: T[];
  labels: LookupManagementLabels;
  create: (name: string) => Promise<T>;
  update: (id: number, name: string) => Promise<T>;
  remove: (id: number) => Promise<void>;
}

export function LookupManagement<T extends LookupItem>({
  initialItems,
  labels,
  create,
  update,
  remove,
}: LookupManagementProps<T>) {
  const router = useRouter();

  // Kept in local state so create/change/delete update the table
  // instantly, without waiting for a full page reload.
  const [items, setItems] = useState(initialItems);

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight underline">{labels.title}</h1>
          <p className="text-muted-foreground">{labels.description}</p>
        </div>
        <CreateItemDialog
          labels={labels}
          create={create}
          onCreated={(newItem) => {
            setItems((current) => [...current, newItem].sort((a, b) => a.name.localeCompare(b.name)));
            router.refresh();
          }}
        />
      </div>

      <div className="overflow-x-auto rounded-md border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="font-bold underline">{labels.tableName}</TableHead>
              <TableHead className="text-right font-bold underline">{labels.tableActions}</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {items.map((item) => (
              <TableRow key={item.id}>
                <TableCell className="font-medium">{item.name}</TableCell>
                <TableCell>
                  <div className="flex justify-end gap-1">
                    <ChangeItemDialog
                      item={item}
                      labels={labels}
                      update={update}
                      onChanged={(updatedItem) => {
                        setItems((current) =>
                          current
                            .map((current_item) => (current_item.id === updatedItem.id ? updatedItem : current_item))
                            .sort((a, b) => a.name.localeCompare(b.name)),
                        );
                        router.refresh();
                      }}
                    />
                    <DeleteItemAlertDialog
                      item={item}
                      labels={labels}
                      remove={remove}
                      onDeleted={(deletedItemId) => {
                        setItems((current) => current.filter((current_item) => current_item.id !== deletedItemId));
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

interface CreateItemDialogProps<T extends LookupItem> {
  labels: LookupManagementLabels;
  create: (name: string) => Promise<T>;
  onCreated: (item: T) => void;
}

function CreateItemDialog<T extends LookupItem>({ labels, create, onCreated }: CreateItemDialogProps<T>) {
  const [isOpen, setIsOpen] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [name, setName] = useState("");

  async function handleSubmit() {
    setIsSubmitting(true);
    try {
      const newItem = await create(name.trim());
      toast.success(labels.itemCreated);
      onCreated(newItem);
      setIsOpen(false);
      setName("");
    } catch (error) {
      const message = error instanceof ApiError ? error.message : labels.createFailed;
      toast.error(message);
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <Dialog open={isOpen} onOpenChange={setIsOpen}>
      <DialogTrigger render={<Button>{labels.newItem}</Button>} />
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{labels.createTitle}</DialogTitle>
          <DialogDescription>{labels.createDescription}</DialogDescription>
        </DialogHeader>

        <div className="flex flex-col gap-2">
          <Label htmlFor="new-lookup-item-name">{labels.nameLabel}</Label>
          <Input id="new-lookup-item-name" value={name} onChange={(event) => setName(event.target.value)} />
        </div>

        <DialogFooter>
          <Button onClick={handleSubmit} disabled={isSubmitting || !name.trim()}>
            {labels.newItem}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

interface ChangeItemDialogProps<T extends LookupItem> {
  item: T;
  labels: LookupManagementLabels;
  update: (id: number, name: string) => Promise<T>;
  onChanged: (item: T) => void;
}

function ChangeItemDialog<T extends LookupItem>({ item, labels, update, onChanged }: ChangeItemDialogProps<T>) {
  const [isOpen, setIsOpen] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [name, setName] = useState(item.name);

  function handleOpenChange(open: boolean) {
    setIsOpen(open);
    if (open) {
      // Start from the item's latest known name each time the dialog is
      // opened, in case it changed since last time.
      setName(item.name);
    }
  }

  async function handleSubmit() {
    setIsSubmitting(true);
    try {
      const updatedItem = await update(item.id, name.trim());
      toast.success(labels.itemUpdated);
      onChanged(updatedItem);
      setIsOpen(false);
    } catch (error) {
      const message = error instanceof ApiError ? error.message : labels.updateFailed;
      toast.error(message);
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <Dialog open={isOpen} onOpenChange={handleOpenChange}>
      <DialogTrigger
        render={
          <Button variant="ghost" size="icon" aria-label={labels.change} title={labels.change}>
            <Pencil className="size-4" />
          </Button>
        }
      />
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{labels.changeTitle}</DialogTitle>
          <DialogDescription>{labels.changeDescription}</DialogDescription>
        </DialogHeader>

        <div className="flex flex-col gap-2">
          <Label htmlFor={`change-lookup-item-name-${item.id}`}>{labels.nameLabel}</Label>
          <Input
            id={`change-lookup-item-name-${item.id}`}
            value={name}
            onChange={(event) => setName(event.target.value)}
          />
        </div>

        <DialogFooter>
          <Button onClick={handleSubmit} disabled={isSubmitting || !name.trim()}>
            {labels.change}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

interface DeleteItemAlertDialogProps<T extends LookupItem> {
  item: T;
  labels: LookupManagementLabels;
  remove: (id: number) => Promise<void>;
  onDeleted: (itemId: number) => void;
}

function DeleteItemAlertDialog<T extends LookupItem>({ item, labels, remove, onDeleted }: DeleteItemAlertDialogProps<T>) {
  const [isOpen, setIsOpen] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);

  async function handleConfirmDelete() {
    setIsDeleting(true);
    try {
      await remove(item.id);
      toast.success(labels.itemDeleted);
      onDeleted(item.id);
      setIsOpen(false);
    } catch (error) {
      const message = error instanceof ApiError ? error.message : labels.deleteFailed;
      toast.error(message);
    } finally {
      setIsDeleting(false);
    }
  }

  return (
    <AlertDialog open={isOpen} onOpenChange={setIsOpen}>
      <AlertDialogTrigger
        render={
          <Button variant="ghost" size="icon" aria-label={labels.delete} title={labels.delete}>
            <Trash2 className="size-4 text-destructive" />
          </Button>
        }
      />
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>{labels.deleteConfirmTitle}</AlertDialogTitle>
          <AlertDialogDescription>{labels.deleteConfirmDescription(item.name)}</AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel>{labels.cancel}</AlertDialogCancel>
          <AlertDialogAction variant="destructive" disabled={isDeleting} onClick={handleConfirmDelete}>
            {labels.delete}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}
