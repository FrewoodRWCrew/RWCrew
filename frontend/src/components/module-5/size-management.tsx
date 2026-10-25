"use client";

// Atelier's "Masterdata > Artikelen > Maten" screen: the sizes an article
// can be ticked in. A size is a name plus a fit (Dames/Heren/Unisex), so
// "M · Dames" and "M · Heren" are separate rows. A filter shows one fit;
// buttons only appear for the rights the user has (the backend checks too).

import { useMemo, useState } from "react";
import { Pencil, Trash2 } from "lucide-react";
import { useTranslations } from "next-intl";
import { toast } from "sonner";
import { useRouter } from "@/i18n/navigation";
import { ApiError, createAtelierSize, deleteAtelierSize, updateAtelierSize } from "@/lib/api";
import type { AtelierFit, AtelierSize, AtelierSizeInput } from "@/lib/types";
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
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { ATELIER_FITS, sortSizes } from "@/components/module-5/atelier-sizes";

// The filter's "every fit" choice (Base UI's Select needs a non-empty value).
const ALL_FITS = "all";

const EMPTY_FORM: AtelierSizeInput = { name: "", fit: "unisex", sort_order: 0, active: true };

interface SizeManagementProps {
  initialSizes: AtelierSize[];
  canCreate: boolean;
  canEdit: boolean;
  canDelete: boolean;
}

export function SizeManagement({ initialSizes, canCreate, canEdit, canDelete }: SizeManagementProps) {
  const t = useTranslations("atelier.sizes");
  const tFit = useTranslations("atelier.fits");
  const router = useRouter();

  // Kept in local state so changes show instantly, without a page reload.
  const [sizes, setSizes] = useState(() => sortSizes(initialSizes));
  const [fitFilter, setFitFilter] = useState<string>(ALL_FITS);

  const shownSizes = useMemo(
    () => (fitFilter === ALL_FITS ? sizes : sizes.filter((size) => size.fit === fitFilter)),
    [sizes, fitFilter],
  );

  function upsert(saved: AtelierSize) {
    setSizes((current) => sortSizes([...current.filter((size) => size.id !== saved.id), saved]));
    router.refresh();
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight underline">{t("title")}</h1>
          <p className="text-muted-foreground">{t("description")}</p>
        </div>
        {canCreate && <SizeFormDialog trigger={<Button>{t("newSize")}</Button>} onSaved={upsert} />}
      </div>

      <div className="flex w-48 flex-col gap-2">
        <Label htmlFor="atelier-size-fit-filter">{t("fitFilterLabel")}</Label>
        <Select value={fitFilter} onValueChange={(value) => setFitFilter(value ?? ALL_FITS)}>
          <SelectTrigger id="atelier-size-fit-filter">
            <SelectValue>
              {(value: string | null) => (value && value !== ALL_FITS ? tFit(value as AtelierFit) : t("allFits"))}
            </SelectValue>
          </SelectTrigger>
          <SelectContent>
            <SelectItem value={ALL_FITS}>{t("allFits")}</SelectItem>
            {ATELIER_FITS.map((fit) => (
              <SelectItem key={fit} value={fit}>
                {tFit(fit)}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <div className="rounded-md border [&>div]:max-h-[65vh] [&>div]:overflow-y-auto">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="sticky top-0 z-20 bg-background font-bold underline">{t("columnName")}</TableHead>
              <TableHead className="sticky top-0 z-20 bg-background font-bold underline">{t("columnFit")}</TableHead>
              <TableHead className="sticky top-0 z-20 bg-background font-bold underline">{t("columnOrder")}</TableHead>
              <TableHead className="sticky top-0 z-20 bg-background font-bold underline">{t("columnActive")}</TableHead>
              <TableHead className="sticky top-0 right-0 z-30 bg-background text-right font-bold underline">
                {t("tableActions")}
              </TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {shownSizes.length === 0 && (
              <TableRow>
                <TableCell colSpan={5} className="text-center text-muted-foreground">
                  {t("empty")}
                </TableCell>
              </TableRow>
            )}
            {shownSizes.map((size) => (
              <TableRow key={size.id} className="group">
                <TableCell className="font-medium">{size.name}</TableCell>
                <TableCell>{tFit(size.fit)}</TableCell>
                <TableCell className="text-muted-foreground">{size.sort_order}</TableCell>
                <TableCell>
                  {size.active ? t("activeYes") : <Badge variant="secondary">{t("activeNo")}</Badge>}
                </TableCell>
                <TableCell className="sticky right-0 z-10 bg-background group-hover:bg-muted/50">
                  <div className="flex justify-end gap-1">
                    {canEdit && (
                      <SizeFormDialog
                        size={size}
                        trigger={
                          <Button variant="ghost" size="icon" aria-label={t("change")} title={t("change")}>
                            <Pencil className="size-4" />
                          </Button>
                        }
                        onSaved={upsert}
                      />
                    )}
                    {canDelete && (
                      <DeleteSizeDialog
                        size={size}
                        onDeleted={(sizeId) => {
                          setSizes((current) => current.filter((item) => item.id !== sizeId));
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

interface SizeFormDialogProps {
  size?: AtelierSize;
  trigger: React.ReactElement;
  onSaved: (size: AtelierSize) => void;
}

function SizeFormDialog({ size, trigger, onSaved }: SizeFormDialogProps) {
  const t = useTranslations("atelier.sizes");
  const tFit = useTranslations("atelier.fits");
  const isEditing = size !== undefined;
  const [isOpen, setIsOpen] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [form, setForm] = useState<AtelierSizeInput>(EMPTY_FORM);

  function handleOpenChange(open: boolean) {
    setIsOpen(open);
    if (open) {
      // Start from the size's latest values every time the dialog opens.
      setForm(size ? { name: size.name, fit: size.fit, sort_order: size.sort_order, active: size.active } : EMPTY_FORM);
    }
  }

  async function handleSubmit() {
    setIsSubmitting(true);
    try {
      const payload = { ...form, name: form.name.trim() };
      const saved = isEditing ? await updateAtelierSize(size.id, payload) : await createAtelierSize(payload);
      toast.success(isEditing ? t("sizeUpdated") : t("sizeCreated"));
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

        <div className="grid grid-cols-2 gap-4">
          <div className="flex flex-col gap-2">
            <Label htmlFor="atelier-size-name">
              {t("nameLabel")} <span aria-hidden="true" className="text-destructive">*</span>
            </Label>
            <Input
              id="atelier-size-name"
              value={form.name}
              placeholder="M"
              onChange={(event) => setForm((current) => ({ ...current, name: event.target.value }))}
            />
          </div>
          <div className="flex flex-col gap-2">
            <Label htmlFor="atelier-size-fit">
              {t("fitLabel")} <span aria-hidden="true" className="text-destructive">*</span>
            </Label>
            <Select
              value={form.fit}
              onValueChange={(value) => value && setForm((current) => ({ ...current, fit: value as AtelierFit }))}
            >
              <SelectTrigger id="atelier-size-fit" className="w-full">
                <SelectValue>{(value: string | null) => (value ? tFit(value as AtelierFit) : "")}</SelectValue>
              </SelectTrigger>
              <SelectContent>
                {ATELIER_FITS.map((fit) => (
                  <SelectItem key={fit} value={fit}>
                    {tFit(fit)}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="flex flex-col gap-2">
            <Label htmlFor="atelier-size-order">{t("orderLabel")}</Label>
            <Input
              id="atelier-size-order"
              type="number"
              min={0}
              step={1}
              value={form.sort_order}
              onChange={(event) =>
                setForm((current) => ({
                  ...current,
                  sort_order: Math.max(0, Number.parseInt(event.target.value, 10) || 0),
                }))
              }
            />
          </div>
          <div className="flex items-end gap-2 pb-2">
            <Checkbox
              id="atelier-size-active"
              checked={form.active}
              onCheckedChange={(checked) => setForm((current) => ({ ...current, active: checked === true }))}
            />
            <Label htmlFor="atelier-size-active">{t("activeLabel")}</Label>
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

interface DeleteSizeDialogProps {
  size: AtelierSize;
  onDeleted: (sizeId: number) => void;
}

function DeleteSizeDialog({ size, onDeleted }: DeleteSizeDialogProps) {
  const t = useTranslations("atelier.sizes");
  const tFit = useTranslations("atelier.fits");
  const tCommon = useTranslations("common");
  const [isOpen, setIsOpen] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);

  async function handleConfirmDelete() {
    setIsDeleting(true);
    try {
      await deleteAtelierSize(size.id);
      toast.success(t("sizeDeleted"));
      onDeleted(size.id);
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
          <AlertDialogDescription>
            {t("deleteConfirmDescription", { name: `${size.name} · ${tFit(size.fit)}` })}
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
