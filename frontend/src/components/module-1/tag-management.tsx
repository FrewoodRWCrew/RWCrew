"use client";

// TagScan's "TagManagement" screen: a table of registered RFID tags with
// add/change/delete, following the same dialog/table pattern as
// MasterData's products-management.tsx. The table shows every column of
// the tag registry with a per-column text/select filter in the row right
// under the header; the surrounding Table component already scrolls
// horizontally (see ui/table.tsx) so the wide row stays usable.

import { useMemo, useState } from "react";
import { Pencil, Trash2 } from "lucide-react";
import { useTranslations } from "next-intl";
import { toast } from "sonner";
import { useRouter } from "@/i18n/navigation";
import { ApiError, createRfidTag, deleteRfidTag, updateRfidTag } from "@/lib/api";
import { API_BASE_URL } from "@/lib/config";
import type { Product, RfidTag, RfidTagInput, RfidTagStatus } from "@/lib/types";
import { TagImportDialog } from "@/components/module-1/tag-import-dialog";
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
import { Button, buttonVariants } from "@/components/ui/button";
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
import { Textarea } from "@/components/ui/textarea";

interface TagManagementProps {
  initialTags: RfidTag[];
  products: Product[];
}

const STATUS_VALUES: RfidTagStatus[] = ["active", "inactive", "lost", "damaged", "retired"];

// Base UI's Select needs every item to have a non-empty value, so "no
// selection" is represented by this sentinel string instead of "".
const NO_SELECTION_VALUE = "none";
// Same idea for the filter row's "don't filter by this" option.
const ALL_VALUE = "all";

const EMPTY_FORM: RfidTagInput = {
  epc_uid: "",
  status: "active",
  assigned_product_id: null,
  assigned_serial_number: "",
  date_assigned: "",
  last_read_at: "",
  last_reader_id: "",
  last_location: "",
  manufacturer: "",
  batch_number: "",
  notes_1: "",
  notes_2: "",
  notes_3: "",
  notes_4: "",
  notes_5: "",
};

/** Plain string slicing instead of toLocaleDateString()/toLocaleString():
 * those depend on the runtime's default locale and the Date object's
 * timezone conversion, both of which differ between the server (Node,
 * during SSR) and the browser (during hydration) — causing a hydration
 * mismatch. Slicing the already-ISO string is deterministic everywhere.
 */
function formatDate(isoDate: string): string {
  return isoDate.slice(0, 10);
}

function formatDateTime(isoDateTime: string): string {
  return isoDateTime.slice(0, 16).replace("T", " ");
}

/** Case-insensitive substring match, used by every free-text filter cell.
 * `null`/empty field values never match a non-empty filter. */
function textMatches(fieldValue: string | null, filterValue: string): boolean {
  if (!filterValue) return true;
  return (fieldValue ?? "").toLowerCase().includes(filterValue.toLowerCase());
}

/** ISO datetimes from the backend are longer than the "YYYY-MM-DDTHH:mm"
 * shape an <input type="datetime-local"> needs — trim to that.
 */
function toDatetimeLocalValue(value: string | null): string {
  return value ? value.slice(0, 16) : "";
}

function toFormValues(tag: RfidTag): RfidTagInput {
  return {
    epc_uid: tag.epc_uid,
    status: tag.status,
    assigned_product_id: tag.assigned_product_id,
    assigned_serial_number: tag.assigned_serial_number ?? "",
    date_assigned: tag.date_assigned ?? "",
    last_read_at: toDatetimeLocalValue(tag.last_read_at),
    last_reader_id: tag.last_reader_id ?? "",
    last_location: tag.last_location ?? "",
    manufacturer: tag.manufacturer ?? "",
    batch_number: tag.batch_number ?? "",
    notes_1: tag.notes_1 ?? "",
    notes_2: tag.notes_2 ?? "",
    notes_3: tag.notes_3 ?? "",
    notes_4: tag.notes_4 ?? "",
    notes_5: tag.notes_5 ?? "",
  };
}

/** Empty-string form fields mean "not set" — turn those into null for
 * the two date fields specifically, since the backend rejects "" as a date.
 */
function toPayload(form: RfidTagInput): RfidTagInput {
  return {
    ...form,
    date_assigned: form.date_assigned || null,
    last_read_at: form.last_read_at || null,
  };
}

export function TagManagement({ initialTags, products }: TagManagementProps) {
  const t = useTranslations("tagscan.tagManagement");
  const router = useRouter();

  const [tags, setTags] = useState(initialTags);
  const [epcFilter, setEpcFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState(ALL_VALUE);
  const [productFilter, setProductFilter] = useState(ALL_VALUE);
  const [serialNumberFilter, setSerialNumberFilter] = useState("");
  const [dateRegisteredFilter, setDateRegisteredFilter] = useState("");
  const [dateAssignedFilter, setDateAssignedFilter] = useState("");
  const [lastReadAtFilter, setLastReadAtFilter] = useState("");
  const [lastReaderIdFilter, setLastReaderIdFilter] = useState("");
  const [lastLocationFilter, setLastLocationFilter] = useState("");
  const [manufacturerFilter, setManufacturerFilter] = useState("");
  const [batchNumberFilter, setBatchNumberFilter] = useState("");
  const [notes1Filter, setNotes1Filter] = useState("");
  const [notes2Filter, setNotes2Filter] = useState("");
  const [notes3Filter, setNotes3Filter] = useState("");
  const [notes4Filter, setNotes4Filter] = useState("");
  const [notes5Filter, setNotes5Filter] = useState("");
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set());

  function productLabelFor(productId: number | null) {
    return products.find((product) => product.id === productId)?.name ?? "";
  }

  const filteredTags = useMemo(() => {
    return tags.filter((tag) => {
      if (epcFilter && !tag.epc_uid.toLowerCase().includes(epcFilter.toLowerCase())) return false;
      if (statusFilter !== ALL_VALUE && tag.status !== statusFilter) return false;
      if (productFilter !== ALL_VALUE && String(tag.assigned_product_id ?? "") !== productFilter) return false;
      if (!textMatches(tag.assigned_serial_number, serialNumberFilter)) return false;
      if (!textMatches(formatDate(tag.date_registered), dateRegisteredFilter)) return false;
      if (!textMatches(tag.date_assigned, dateAssignedFilter)) return false;
      if (!textMatches(tag.last_read_at ? formatDateTime(tag.last_read_at) : null, lastReadAtFilter)) return false;
      if (!textMatches(tag.last_reader_id, lastReaderIdFilter)) return false;
      if (!textMatches(tag.last_location, lastLocationFilter)) return false;
      if (!textMatches(tag.manufacturer, manufacturerFilter)) return false;
      if (!textMatches(tag.batch_number, batchNumberFilter)) return false;
      if (!textMatches(tag.notes_1, notes1Filter)) return false;
      if (!textMatches(tag.notes_2, notes2Filter)) return false;
      if (!textMatches(tag.notes_3, notes3Filter)) return false;
      if (!textMatches(tag.notes_4, notes4Filter)) return false;
      if (!textMatches(tag.notes_5, notes5Filter)) return false;
      return true;
    });
  }, [
    tags,
    epcFilter,
    statusFilter,
    productFilter,
    serialNumberFilter,
    dateRegisteredFilter,
    dateAssignedFilter,
    lastReadAtFilter,
    lastReaderIdFilter,
    lastLocationFilter,
    manufacturerFilter,
    batchNumberFilter,
    notes1Filter,
    notes2Filter,
    notes3Filter,
    notes4Filter,
    notes5Filter,
  ]);

  const filteredIds = useMemo(() => filteredTags.map((tag) => tag.id), [filteredTags]);
  const allFilteredSelected = filteredIds.length > 0 && filteredIds.every((id) => selectedIds.has(id));
  const someFilteredSelected = filteredIds.some((id) => selectedIds.has(id));

  function toggleSelectAll(checked: boolean) {
    setSelectedIds((current) => {
      const next = new Set(current);
      for (const id of filteredIds) {
        if (checked) next.add(id);
        else next.delete(id);
      }
      return next;
    });
  }

  function toggleSelectOne(tagId: number, checked: boolean) {
    setSelectedIds((current) => {
      const next = new Set(current);
      if (checked) next.add(tagId);
      else next.delete(tagId);
      return next;
    });
  }

  function upsert(updated: RfidTag) {
    setTags((current) => {
      const exists = current.some((tag) => tag.id === updated.id);
      return exists
        ? current.map((tag) => (tag.id === updated.id ? updated : tag))
        : [...current, updated].sort((a, b) => a.epc_uid.localeCompare(b.epc_uid));
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
        <div className="flex items-center gap-2">
          <a
            href={`${API_BASE_URL}/api/modules/module-1/tags/template`}
            className={buttonVariants({ variant: "outline" })}
          >
            {t("downloadTemplate")}
          </a>
          <TagImportDialog trigger={<Button variant="outline">{t("importCsv")}</Button>} />
          <TagFormDialog trigger={<Button>{t("newTag")}</Button>} onSaved={upsert} products={products} />
        </div>
      </div>

      <div className="rounded-md border [&>div]:max-h-[65vh] [&>div]:overflow-y-auto">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="sticky top-0 z-20 bg-background">
                <Checkbox
                  checked={allFilteredSelected}
                  indeterminate={someFilteredSelected && !allFilteredSelected}
                  onCheckedChange={(checked) => toggleSelectAll(checked === true)}
                  aria-label={t("selectAll")}
                />
              </TableHead>
              <TableHead className="sticky top-0 z-20 bg-background font-bold underline">{t("columnEpcUid")}</TableHead>
              <TableHead className="sticky top-0 z-20 bg-background font-bold underline">{t("columnStatus")}</TableHead>
              <TableHead className="sticky top-0 z-20 bg-background font-bold underline">{t("columnAssignedProduct")}</TableHead>
              <TableHead className="sticky top-0 z-20 bg-background font-bold underline">{t("columnAssignedSerialNumber")}</TableHead>
              <TableHead className="sticky top-0 z-20 bg-background font-bold underline">{t("columnDateRegistered")}</TableHead>
              <TableHead className="sticky top-0 z-20 bg-background font-bold underline">{t("columnDateAssigned")}</TableHead>
              <TableHead className="sticky top-0 z-20 bg-background font-bold underline">{t("columnLastReadAt")}</TableHead>
              <TableHead className="sticky top-0 z-20 bg-background font-bold underline">{t("columnLastReaderId")}</TableHead>
              <TableHead className="sticky top-0 z-20 bg-background font-bold underline">{t("columnLastLocation")}</TableHead>
              <TableHead className="sticky top-0 z-20 bg-background font-bold underline">{t("columnManufacturer")}</TableHead>
              <TableHead className="sticky top-0 z-20 bg-background font-bold underline">{t("columnBatchNumber")}</TableHead>
              <TableHead className="sticky top-0 z-20 bg-background font-bold underline">{t("columnNotes1")}</TableHead>
              <TableHead className="sticky top-0 z-20 bg-background font-bold underline">{t("columnNotes2")}</TableHead>
              <TableHead className="sticky top-0 z-20 bg-background font-bold underline">{t("columnNotes3")}</TableHead>
              <TableHead className="sticky top-0 z-20 bg-background font-bold underline">{t("columnNotes4")}</TableHead>
              <TableHead className="sticky top-0 z-20 bg-background font-bold underline">{t("columnNotes5")}</TableHead>
              {/* Actions stays pinned to the right edge while the rest of
                  the row scrolls horizontally — with 16 data columns now
                  shown, an unpinned Actions cell would scroll out of
                  view, leaving Edit/Delete unreachable without first
                  scrolling all the way right. */}
              <TableHead className="sticky top-0 right-0 z-30 bg-background text-right font-bold underline">
                {t("tableActions")}
              </TableHead>
            </TableRow>
            {/* The filter row: each control sits directly under the
                column it filters. Actions has no filter, so it gets an
                empty cell to keep alignment exact. */}
            <TableRow>
              <TableHead className="sticky top-10 z-20 bg-background" />
              <TableHead className="sticky top-10 z-20 bg-background">
                <Input
                  aria-label={t("filterEpcUid")}
                  placeholder={t("filterEpcUid")}
                  className="h-8 w-full min-w-32 font-normal"
                  value={epcFilter}
                  onChange={(event) => setEpcFilter(event.target.value)}
                />
              </TableHead>
              <TableHead className="sticky top-10 z-20 bg-background">
                <Select value={statusFilter} onValueChange={(value) => setStatusFilter(value ?? ALL_VALUE)}>
                  <SelectTrigger aria-label={t("filterStatus")} className="h-8 w-full font-normal">
                    <SelectValue>
                      {(value: string | null) =>
                        value && value !== ALL_VALUE ? t(`status.${value}`) : t("allStatuses")
                      }
                    </SelectValue>
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value={ALL_VALUE}>{t("allStatuses")}</SelectItem>
                    {STATUS_VALUES.map((statusValue) => (
                      <SelectItem key={statusValue} value={statusValue}>
                        {t(`status.${statusValue}`)}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </TableHead>
              <TableHead className="sticky top-10 z-20 bg-background">
                <Select value={productFilter} onValueChange={(value) => setProductFilter(value ?? ALL_VALUE)}>
                  <SelectTrigger aria-label={t("filterProduct")} className="h-8 w-full font-normal">
                    <SelectValue>
                      {(value: string | null) =>
                        value && value !== ALL_VALUE
                          ? (products.find((product) => String(product.id) === value)?.name ?? t("allProducts"))
                          : t("allProducts")
                      }
                    </SelectValue>
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value={ALL_VALUE}>{t("allProducts")}</SelectItem>
                    {products.map((product) => (
                      <SelectItem key={product.id} value={String(product.id)}>
                        {product.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </TableHead>
              <TableHead className="sticky top-10 z-20 bg-background">
                <Input
                  aria-label={t("filterAssignedSerialNumber")}
                  placeholder={t("filterAssignedSerialNumber")}
                  className="h-8 w-full min-w-32 font-normal"
                  value={serialNumberFilter}
                  onChange={(event) => setSerialNumberFilter(event.target.value)}
                />
              </TableHead>
              <TableHead className="sticky top-10 z-20 bg-background">
                <Input
                  aria-label={t("filterDateRegistered")}
                  placeholder={t("filterDateRegistered")}
                  className="h-8 w-full min-w-32 font-normal"
                  value={dateRegisteredFilter}
                  onChange={(event) => setDateRegisteredFilter(event.target.value)}
                />
              </TableHead>
              <TableHead className="sticky top-10 z-20 bg-background">
                <Input
                  aria-label={t("filterDateAssigned")}
                  placeholder={t("filterDateAssigned")}
                  className="h-8 w-full min-w-32 font-normal"
                  value={dateAssignedFilter}
                  onChange={(event) => setDateAssignedFilter(event.target.value)}
                />
              </TableHead>
              <TableHead className="sticky top-10 z-20 bg-background">
                <Input
                  aria-label={t("filterLastReadAt")}
                  placeholder={t("filterLastReadAt")}
                  className="h-8 w-full min-w-32 font-normal"
                  value={lastReadAtFilter}
                  onChange={(event) => setLastReadAtFilter(event.target.value)}
                />
              </TableHead>
              <TableHead className="sticky top-10 z-20 bg-background">
                <Input
                  aria-label={t("filterLastReaderId")}
                  placeholder={t("filterLastReaderId")}
                  className="h-8 w-full min-w-32 font-normal"
                  value={lastReaderIdFilter}
                  onChange={(event) => setLastReaderIdFilter(event.target.value)}
                />
              </TableHead>
              <TableHead className="sticky top-10 z-20 bg-background">
                <Input
                  aria-label={t("filterLastLocation")}
                  placeholder={t("filterLastLocation")}
                  className="h-8 w-full min-w-32 font-normal"
                  value={lastLocationFilter}
                  onChange={(event) => setLastLocationFilter(event.target.value)}
                />
              </TableHead>
              <TableHead className="sticky top-10 z-20 bg-background">
                <Input
                  aria-label={t("filterManufacturer")}
                  placeholder={t("filterManufacturer")}
                  className="h-8 w-full min-w-32 font-normal"
                  value={manufacturerFilter}
                  onChange={(event) => setManufacturerFilter(event.target.value)}
                />
              </TableHead>
              <TableHead className="sticky top-10 z-20 bg-background">
                <Input
                  aria-label={t("filterBatchNumber")}
                  placeholder={t("filterBatchNumber")}
                  className="h-8 w-full min-w-32 font-normal"
                  value={batchNumberFilter}
                  onChange={(event) => setBatchNumberFilter(event.target.value)}
                />
              </TableHead>
              <TableHead className="sticky top-10 z-20 bg-background">
                <Input
                  aria-label={t("filterNotes1")}
                  placeholder={t("filterNotes1")}
                  className="h-8 w-full min-w-32 font-normal"
                  value={notes1Filter}
                  onChange={(event) => setNotes1Filter(event.target.value)}
                />
              </TableHead>
              <TableHead className="sticky top-10 z-20 bg-background">
                <Input
                  aria-label={t("filterNotes2")}
                  placeholder={t("filterNotes2")}
                  className="h-8 w-full min-w-32 font-normal"
                  value={notes2Filter}
                  onChange={(event) => setNotes2Filter(event.target.value)}
                />
              </TableHead>
              <TableHead className="sticky top-10 z-20 bg-background">
                <Input
                  aria-label={t("filterNotes3")}
                  placeholder={t("filterNotes3")}
                  className="h-8 w-full min-w-32 font-normal"
                  value={notes3Filter}
                  onChange={(event) => setNotes3Filter(event.target.value)}
                />
              </TableHead>
              <TableHead className="sticky top-10 z-20 bg-background">
                <Input
                  aria-label={t("filterNotes4")}
                  placeholder={t("filterNotes4")}
                  className="h-8 w-full min-w-32 font-normal"
                  value={notes4Filter}
                  onChange={(event) => setNotes4Filter(event.target.value)}
                />
              </TableHead>
              <TableHead className="sticky top-10 z-20 bg-background">
                <Input
                  aria-label={t("filterNotes5")}
                  placeholder={t("filterNotes5")}
                  className="h-8 w-full min-w-32 font-normal"
                  value={notes5Filter}
                  onChange={(event) => setNotes5Filter(event.target.value)}
                />
              </TableHead>
              <TableHead className="sticky top-10 right-0 z-30 bg-background" />
            </TableRow>
          </TableHeader>
          <TableBody>
            {filteredTags.map((tag) => (
              <TableRow key={tag.id} className="group">
                <TableCell>
                  <Checkbox
                    checked={selectedIds.has(tag.id)}
                    onCheckedChange={(checked) => toggleSelectOne(tag.id, checked === true)}
                    aria-label={t("selectRow", { epcUid: tag.epc_uid })}
                  />
                </TableCell>
                <TableCell className="font-medium">{tag.epc_uid}</TableCell>
                <TableCell className="text-muted-foreground">{t(`status.${tag.status}`)}</TableCell>
                <TableCell className="text-muted-foreground">{productLabelFor(tag.assigned_product_id)}</TableCell>
                <TableCell className="text-muted-foreground">{tag.assigned_serial_number}</TableCell>
                <TableCell className="text-muted-foreground">
                  {formatDate(tag.date_registered)}
                </TableCell>
                <TableCell className="text-muted-foreground">{tag.date_assigned}</TableCell>
                <TableCell className="text-muted-foreground">
                  {tag.last_read_at ? formatDateTime(tag.last_read_at) : ""}
                </TableCell>
                <TableCell className="text-muted-foreground">{tag.last_reader_id}</TableCell>
                <TableCell className="text-muted-foreground">{tag.last_location}</TableCell>
                <TableCell className="text-muted-foreground">{tag.manufacturer}</TableCell>
                <TableCell className="text-muted-foreground">{tag.batch_number}</TableCell>
                <TableCell className="text-muted-foreground">{tag.notes_1}</TableCell>
                <TableCell className="text-muted-foreground">{tag.notes_2}</TableCell>
                <TableCell className="text-muted-foreground">{tag.notes_3}</TableCell>
                <TableCell className="text-muted-foreground">{tag.notes_4}</TableCell>
                <TableCell className="text-muted-foreground">{tag.notes_5}</TableCell>
                <TableCell className="sticky right-0 z-10 bg-background group-hover:bg-muted/50">
                  <div className="flex justify-end gap-1">
                    <TagFormDialog
                      tag={tag}
                      trigger={
                        <Button variant="ghost" size="icon" aria-label={t("change")} title={t("change")}>
                          <Pencil className="size-4" />
                        </Button>
                      }
                      onSaved={upsert}
                      products={products}
                    />
                    <DeleteTagAlertDialog
                      tag={tag}
                      onDeleted={(tagId) => {
                        setTags((current) => current.filter((item) => item.id !== tagId));
                        setSelectedIds((current) => {
                          const next = new Set(current);
                          next.delete(tagId);
                          return next;
                        });
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

interface TagFormDialogProps {
  tag?: RfidTag;
  trigger: React.ReactElement;
  onSaved: (tag: RfidTag) => void;
  products: Product[];
}

function TagFormDialog({ tag, trigger, onSaved, products }: TagFormDialogProps) {
  const t = useTranslations("tagscan.tagManagement");
  const isEditing = tag !== undefined;
  const [isOpen, setIsOpen] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [form, setForm] = useState<RfidTagInput>(tag ? toFormValues(tag) : EMPTY_FORM);

  function handleOpenChange(open: boolean) {
    setIsOpen(open);
    if (open) {
      // Start from the tag's latest known values each time the dialog
      // is opened, in case they changed since last time.
      setForm(tag ? toFormValues(tag) : EMPTY_FORM);
    }
  }

  function updateField<K extends keyof RfidTagInput>(field: K, value: RfidTagInput[K]) {
    setForm((current) => ({ ...current, [field]: value }));
  }

  async function handleSubmit() {
    setIsSubmitting(true);
    try {
      const payload = toPayload(form);
      const savedTag = isEditing ? await updateRfidTag(tag.id, payload) : await createRfidTag(payload);
      toast.success(isEditing ? t("tagUpdated") : t("tagCreated"));
      onSaved(savedTag);
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
      <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-2xl">
        <DialogHeader>
          <DialogTitle>{isEditing ? t("changeTitle") : t("createTitle")}</DialogTitle>
          <DialogDescription>{isEditing ? t("changeDescription") : t("createDescription")}</DialogDescription>
        </DialogHeader>

        <div className="grid grid-cols-2 gap-4">
          <div className="col-span-2 flex flex-col gap-2">
            <Label htmlFor="tag-epc-uid">{t("epcUidLabel")}</Label>
            <Input id="tag-epc-uid" value={form.epc_uid} onChange={(event) => updateField("epc_uid", event.target.value)} />
          </div>

          <div className="flex flex-col gap-2">
            <Label htmlFor="tag-status">{t("statusLabel")}</Label>
            <Select
              value={form.status ?? "active"}
              onValueChange={(value) => updateField("status", (value ?? "active") as RfidTagStatus)}
            >
              <SelectTrigger id="tag-status">
                <SelectValue>{(value: string | null) => t(`status.${value ?? "active"}`)}</SelectValue>
              </SelectTrigger>
              <SelectContent>
                {STATUS_VALUES.map((statusValue) => (
                  <SelectItem key={statusValue} value={statusValue}>
                    {t(`status.${statusValue}`)}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="flex flex-col gap-2">
            <Label htmlFor="tag-assigned-product">{t("assignedProductLabel")}</Label>
            <Select
              value={form.assigned_product_id ? String(form.assigned_product_id) : NO_SELECTION_VALUE}
              onValueChange={(value) =>
                updateField("assigned_product_id", value && value !== NO_SELECTION_VALUE ? Number(value) : null)
              }
            >
              <SelectTrigger id="tag-assigned-product">
                <SelectValue>
                  {(value: string | null) => products.find((product) => String(product.id) === value)?.name ?? t("noSelection")}
                </SelectValue>
              </SelectTrigger>
              <SelectContent>
                <SelectItem value={NO_SELECTION_VALUE}>{t("noSelection")}</SelectItem>
                {products.map((product) => (
                  <SelectItem key={product.id} value={String(product.id)}>
                    {product.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="flex flex-col gap-2">
            <Label htmlFor="tag-assigned-serial-number">{t("assignedSerialNumberLabel")}</Label>
            <Input
              id="tag-assigned-serial-number"
              value={form.assigned_serial_number ?? ""}
              onChange={(event) => updateField("assigned_serial_number", event.target.value)}
            />
          </div>

          <div className="flex flex-col gap-2">
            <Label htmlFor="tag-date-assigned">{t("dateAssignedLabel")}</Label>
            <Input
              id="tag-date-assigned"
              type="date"
              value={form.date_assigned ?? ""}
              onChange={(event) => updateField("date_assigned", event.target.value)}
            />
          </div>

          <div className="flex flex-col gap-2">
            <Label htmlFor="tag-last-read-at">{t("lastReadAtLabel")}</Label>
            <Input
              id="tag-last-read-at"
              type="datetime-local"
              value={form.last_read_at ?? ""}
              onChange={(event) => updateField("last_read_at", event.target.value)}
            />
          </div>

          <div className="flex flex-col gap-2">
            <Label htmlFor="tag-last-reader-id">{t("lastReaderIdLabel")}</Label>
            <Input
              id="tag-last-reader-id"
              value={form.last_reader_id ?? ""}
              onChange={(event) => updateField("last_reader_id", event.target.value)}
            />
          </div>

          <div className="flex flex-col gap-2">
            <Label htmlFor="tag-last-location">{t("lastLocationLabel")}</Label>
            <Input
              id="tag-last-location"
              value={form.last_location ?? ""}
              onChange={(event) => updateField("last_location", event.target.value)}
            />
          </div>

          <div className="flex flex-col gap-2">
            <Label htmlFor="tag-manufacturer">{t("manufacturerLabel")}</Label>
            <Input
              id="tag-manufacturer"
              value={form.manufacturer ?? ""}
              onChange={(event) => updateField("manufacturer", event.target.value)}
            />
          </div>

          <div className="flex flex-col gap-2">
            <Label htmlFor="tag-batch-number">{t("batchNumberLabel")}</Label>
            <Input
              id="tag-batch-number"
              value={form.batch_number ?? ""}
              onChange={(event) => updateField("batch_number", event.target.value)}
            />
          </div>

          <div className="col-span-2 flex flex-col gap-2">
            <Label htmlFor="tag-notes-1">{t("notes1Label")}</Label>
            <Textarea id="tag-notes-1" value={form.notes_1 ?? ""} onChange={(event) => updateField("notes_1", event.target.value)} />
          </div>
          <div className="col-span-2 flex flex-col gap-2">
            <Label htmlFor="tag-notes-2">{t("notes2Label")}</Label>
            <Textarea id="tag-notes-2" value={form.notes_2 ?? ""} onChange={(event) => updateField("notes_2", event.target.value)} />
          </div>
          <div className="col-span-2 flex flex-col gap-2">
            <Label htmlFor="tag-notes-3">{t("notes3Label")}</Label>
            <Textarea id="tag-notes-3" value={form.notes_3 ?? ""} onChange={(event) => updateField("notes_3", event.target.value)} />
          </div>
          <div className="col-span-2 flex flex-col gap-2">
            <Label htmlFor="tag-notes-4">{t("notes4Label")}</Label>
            <Textarea id="tag-notes-4" value={form.notes_4 ?? ""} onChange={(event) => updateField("notes_4", event.target.value)} />
          </div>
          <div className="col-span-2 flex flex-col gap-2">
            <Label htmlFor="tag-notes-5">{t("notes5Label")}</Label>
            <Textarea id="tag-notes-5" value={form.notes_5 ?? ""} onChange={(event) => updateField("notes_5", event.target.value)} />
          </div>
        </div>

        <DialogFooter>
          <Button onClick={handleSubmit} disabled={isSubmitting || !form.epc_uid}>
            {isEditing ? t("change") : t("newTag")}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

interface DeleteTagAlertDialogProps {
  tag: RfidTag;
  onDeleted: (tagId: number) => void;
}

function DeleteTagAlertDialog({ tag, onDeleted }: DeleteTagAlertDialogProps) {
  const t = useTranslations("tagscan.tagManagement");
  const tCommon = useTranslations("common");
  const [isOpen, setIsOpen] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);

  async function handleConfirmDelete() {
    setIsDeleting(true);
    try {
      await deleteRfidTag(tag.id);
      toast.success(t("tagDeleted"));
      onDeleted(tag.id);
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
          <AlertDialogDescription>{t("deleteConfirmDescription", { epcUid: tag.epc_uid })}</AlertDialogDescription>
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
