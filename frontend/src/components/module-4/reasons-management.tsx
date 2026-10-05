"use client";

// StockMaster's "Instellingen > Redenen": the reasons a person picks when
// stock leaves or changes ("Verbruikt", "Defect", "Telverschil", ...), each
// offered on one booking type (or on all of them). A reason that was ever
// used can't be deleted — make it inactive instead, so old bookings keep it.

import { useState } from "react";
import { Pencil, Plus, Trash2 } from "lucide-react";
import { useTranslations } from "next-intl";
import { toast } from "sonner";
import { createStockMasterReason, deleteStockMasterReason, updateStockMasterReason } from "@/lib/api";
import type { StockMasterMyPermissions, StockMasterReason, StockMasterReasonInput } from "@/lib/types";
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
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { ACTION_ORDER, hasRight, stockErrorMessage } from "@/components/module-4/stockmaster-common";

interface ReasonsManagementProps {
  initialReasons: StockMasterReason[];
  permissions: StockMasterMyPermissions;
}

const ALL_TYPES = "all";

export function ReasonsManagement({ initialReasons, permissions }: ReasonsManagementProps) {
  const t = useTranslations("stockMaster");
  const tReasons = useTranslations("stockMaster.reasons");
  const [reasons, setReasons] = useState(initialReasons);

  function upsert(reason: StockMasterReason) {
    setReasons((current) =>
      [...current.filter((item) => item.id !== reason.id), reason].sort(
        (a, b) => a.sort_order - b.sort_order || a.name.localeCompare(b.name),
      ),
    );
  }

  async function remove(reason: StockMasterReason) {
    try {
      await deleteStockMasterReason(reason.id);
      setReasons((current) => current.filter((item) => item.id !== reason.id));
      toast.success(tReasons("deleted"));
    } catch (error) {
      toast.error(stockErrorMessage(t, error));
    }
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight underline">{tReasons("title")}</h1>
          <p className="text-muted-foreground">{tReasons("description")}</p>
        </div>
        {hasRight(permissions, "reasons", "create") && <ReasonDialog onSaved={upsert} />}
      </div>

      <div className="rounded-md border [&>div]:max-h-[65vh] [&>div]:overflow-y-auto">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="sticky top-0 z-20 bg-background font-bold underline">{tReasons("name")}</TableHead>
              <TableHead className="sticky top-0 z-20 bg-background font-bold underline">{tReasons("appliesTo")}</TableHead>
              <TableHead className="sticky top-0 z-20 bg-background text-right font-bold underline">{tReasons("order")}</TableHead>
              <TableHead className="sticky top-0 z-20 bg-background font-bold underline">{tReasons("status")}</TableHead>
              <TableHead className="sticky top-0 right-0 z-30 bg-background text-right font-bold underline">
                {t("common.actions")}
              </TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {reasons.length === 0 && (
              <TableRow>
                <TableCell colSpan={5} className="py-8 text-center text-muted-foreground">
                  {tReasons("empty")}
                </TableCell>
              </TableRow>
            )}
            {reasons.map((reason) => (
              <TableRow key={reason.id} className="group">
                <TableCell className="font-medium">{reason.name}</TableCell>
                <TableCell>{reason.applies_to ? t(`docTypes.${reason.applies_to}`) : tReasons("allTypes")}</TableCell>
                <TableCell className="text-right tabular-nums">{reason.sort_order}</TableCell>
                <TableCell>
                  {reason.active ? <Badge variant="secondary">{tReasons("active")}</Badge> : <Badge variant="outline">{tReasons("inactive")}</Badge>}
                </TableCell>
                <TableCell className="sticky right-0 z-10 bg-background text-right group-hover:bg-muted/50">
                  <div className="flex justify-end gap-1">
                    {hasRight(permissions, "reasons", "edit") && <ReasonDialog reason={reason} onSaved={upsert} />}
                    {hasRight(permissions, "reasons", "delete") && (
                      <AlertDialog>
                        <AlertDialogTrigger render={<Button variant="ghost" size="icon-sm" aria-label={tReasons("delete")} />}>
                          <Trash2 />
                        </AlertDialogTrigger>
                        <AlertDialogContent>
                          <AlertDialogHeader>
                            <AlertDialogTitle>{tReasons("deleteTitle", { name: reason.name })}</AlertDialogTitle>
                            <AlertDialogDescription>{tReasons("deleteDescription")}</AlertDialogDescription>
                          </AlertDialogHeader>
                          <AlertDialogFooter>
                            <AlertDialogCancel>{t("common.cancel")}</AlertDialogCancel>
                            <AlertDialogAction onClick={() => void remove(reason)}>{tReasons("delete")}</AlertDialogAction>
                          </AlertDialogFooter>
                        </AlertDialogContent>
                      </AlertDialog>
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

interface ReasonDialogProps {
  reason?: StockMasterReason;
  onSaved: (reason: StockMasterReason) => void;
}

/** Add a reason, or change one (when `reason` is given). */
function ReasonDialog({ reason, onSaved }: ReasonDialogProps) {
  const t = useTranslations("stockMaster");
  const tReasons = useTranslations("stockMaster.reasons");
  const [isOpen, setIsOpen] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [form, setForm] = useState<StockMasterReasonInput>(() => toForm(reason));

  function toForm(source?: StockMasterReason): StockMasterReasonInput {
    return {
      name: source?.name ?? "",
      applies_to: source?.applies_to ?? null,
      active: source?.active ?? true,
      sort_order: source?.sort_order ?? 0,
    };
  }

  async function handleSave() {
    setIsSaving(true);
    try {
      const saved = reason ? await updateStockMasterReason(reason.id, form) : await createStockMasterReason(form);
      onSaved(saved);
      toast.success(tReasons("saved"));
      setIsOpen(false);
    } catch (error) {
      toast.error(stockErrorMessage(t, error));
    } finally {
      setIsSaving(false);
    }
  }

  return (
    <Dialog
      open={isOpen}
      onOpenChange={(open) => {
        setIsOpen(open);
        if (open) setForm(toForm(reason));
      }}
    >
      {reason ? (
        <DialogTrigger render={<Button variant="ghost" size="icon-sm" aria-label={tReasons("change")} />}>
          <Pencil />
        </DialogTrigger>
      ) : (
        <DialogTrigger render={<Button />}>
          <Plus />
          {tReasons("new")}
        </DialogTrigger>
      )}
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{reason ? tReasons("change") : tReasons("new")}</DialogTitle>
        </DialogHeader>
        <div className="flex flex-col gap-4">
          <div className="flex flex-col gap-2">
            <Label htmlFor="reason-name">{tReasons("name")}</Label>
            <Input id="reason-name" value={form.name} onChange={(event) => setForm({ ...form, name: event.target.value })} />
          </div>
          <div className="flex flex-col gap-2">
            <Label htmlFor="reason-type">{tReasons("appliesTo")}</Label>
            <Select
              value={form.applies_to ?? ALL_TYPES}
              onValueChange={(value) =>
                setForm({ ...form, applies_to: !value || value === ALL_TYPES ? null : (value as StockMasterReasonInput["applies_to"]) })
              }
            >
              <SelectTrigger id="reason-type" className="w-full">
                <SelectValue>
                  {(value: string | null) => (!value || value === ALL_TYPES ? tReasons("allTypes") : t(`docTypes.${value}`))}
                </SelectValue>
              </SelectTrigger>
              <SelectContent>
                <SelectItem value={ALL_TYPES}>{tReasons("allTypes")}</SelectItem>
                {ACTION_ORDER.map((action) => (
                  <SelectItem key={action} value={action}>
                    {t(`docTypes.${action}`)}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="flex flex-col gap-2">
            <Label htmlFor="reason-order">{tReasons("order")}</Label>
            <Input
              id="reason-order"
              type="number"
              step={1}
              value={form.sort_order}
              onChange={(event) => setForm({ ...form, sort_order: Number.parseInt(event.target.value, 10) || 0 })}
            />
          </div>
          <div className="flex items-center gap-2">
            <Checkbox id="reason-active" checked={form.active} onCheckedChange={(checked) => setForm({ ...form, active: checked === true })} />
            <Label htmlFor="reason-active">{tReasons("active")}</Label>
          </div>
        </div>
        <DialogFooter>
          <Button onClick={() => void handleSave()} disabled={isSaving || !form.name.trim()}>
            {tReasons("save")}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
