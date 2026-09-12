"use client";

// TagScan's "Scanners" screen: a table of registered scanner devices with
// add/change/delete, following the same dialog/table pattern as
// TagManagement (see tag-management.tsx). The table shows every column of
// the scanner registry with a per-column text/select filter in the row
// right under the header; the surrounding Table component already
// scrolls horizontally (see ui/table.tsx) so the wide row stays usable.

import { useMemo, useState } from "react";
import { KeyRound, Pencil, Trash2 } from "lucide-react";
import { useTranslations } from "next-intl";
import { toast } from "sonner";
import { useRouter } from "@/i18n/navigation";
import { API_BASE_URL } from "@/lib/config";
import { ApiError, createScanner, deleteScanner, generateScannerApiKey, revokeScannerApiKey, updateScanner } from "@/lib/api";
import type { ProductType, Scanner, ScannerInput, ScannerTechnology } from "@/lib/types";
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

const INTAKE_UPLOAD_URL = `${API_BASE_URL}/api/public/tagscan-intake`;

async function copyToClipboard(value: string, onSuccess: () => void, onError: () => void) {
  try {
    await navigator.clipboard.writeText(value);
    onSuccess();
  } catch {
    onError();
  }
}

interface ScannerManagementProps {
  initialScanners: Scanner[];
  productTypes: ProductType[];
}

const TECHNOLOGY_VALUES: ScannerTechnology[] = ["Raspberry Pi 3", "Raspberry Pi 4", "Raspberry Pi 5", "Other"];

// Same idea as the filter row's "don't filter by this" option elsewhere.
const ALL_VALUE = "all";

/** The dialog's own form state — same shape as ScannerInput, except
 * type_id is nullable here to represent "no type picked yet" in the
 * Select below. ScannerInput itself stays non-null (a scanner always
 * requires a type on the wire — see its definition in lib/types.ts);
 * handleSubmit below guards against submitting before a type is chosen. */
type ScannerFormState = Omit<ScannerInput, "type_id"> & { type_id: number | null };

function emptyForm(productTypes: ProductType[]): ScannerFormState {
  return {
    scanner: "",
    type_id: productTypes[0]?.id ?? null,
    technology: "Raspberry Pi 4",
    location: "",
    description: "",
    info1: "",
    info2: "",
    info3: "",
  };
}

/** Case-insensitive substring match, used by every free-text filter cell.
 * `null`/empty field values never match a non-empty filter. */
function textMatches(fieldValue: string | null, filterValue: string): boolean {
  if (!filterValue) return true;
  return (fieldValue ?? "").toLowerCase().includes(filterValue.toLowerCase());
}

function toFormValues(scanner: Scanner): ScannerFormState {
  return {
    scanner: scanner.scanner,
    type_id: scanner.type_id,
    technology: scanner.technology,
    location: scanner.location ?? "",
    description: scanner.description ?? "",
    info1: scanner.info1 ?? "",
    info2: scanner.info2 ?? "",
    info3: scanner.info3 ?? "",
  };
}

export function ScannerManagement({ initialScanners, productTypes }: ScannerManagementProps) {
  const t = useTranslations("tagscan.scanners");
  const router = useRouter();

  const [scanners, setScanners] = useState(initialScanners);
  const [scannerFilter, setScannerFilter] = useState("");
  const [typeFilter, setTypeFilter] = useState(ALL_VALUE);
  const [technologyFilter, setTechnologyFilter] = useState(ALL_VALUE);
  const [locationFilter, setLocationFilter] = useState("");
  const [descriptionFilter, setDescriptionFilter] = useState("");
  const [info1Filter, setInfo1Filter] = useState("");
  const [info2Filter, setInfo2Filter] = useState("");
  const [info3Filter, setInfo3Filter] = useState("");

  function typeLabelFor(typeId: number) {
    return productTypes.find((productType) => productType.id === typeId)?.name ?? "";
  }

  const filteredScanners = useMemo(() => {
    return scanners.filter((scanner) => {
      if (scannerFilter && !scanner.scanner.toLowerCase().includes(scannerFilter.toLowerCase())) return false;
      if (typeFilter !== ALL_VALUE && String(scanner.type_id) !== typeFilter) return false;
      if (technologyFilter !== ALL_VALUE && scanner.technology !== technologyFilter) return false;
      if (!textMatches(scanner.location, locationFilter)) return false;
      if (!textMatches(scanner.description, descriptionFilter)) return false;
      if (!textMatches(scanner.info1, info1Filter)) return false;
      if (!textMatches(scanner.info2, info2Filter)) return false;
      if (!textMatches(scanner.info3, info3Filter)) return false;
      return true;
    });
  }, [
    scanners,
    scannerFilter,
    typeFilter,
    technologyFilter,
    locationFilter,
    descriptionFilter,
    info1Filter,
    info2Filter,
    info3Filter,
  ]);

  function upsert(updated: Scanner) {
    setScanners((current) => {
      const exists = current.some((scanner) => scanner.id === updated.id);
      return exists
        ? current.map((scanner) => (scanner.id === updated.id ? updated : scanner))
        : [...current, updated].sort((a, b) => a.scanner.localeCompare(b.scanner));
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
        <ScannerFormDialog
          trigger={<Button>{t("newScanner")}</Button>}
          onSaved={upsert}
          productTypes={productTypes}
        />
      </div>

      <div className="rounded-md border [&>div]:max-h-[65vh] [&>div]:overflow-y-auto">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="sticky top-0 z-20 bg-background font-bold underline">{t("columnScanner")}</TableHead>
              <TableHead className="sticky top-0 z-20 bg-background font-bold underline">{t("columnType")}</TableHead>
              <TableHead className="sticky top-0 z-20 bg-background font-bold underline">{t("columnTechnology")}</TableHead>
              <TableHead className="sticky top-0 z-20 bg-background font-bold underline">{t("columnLocation")}</TableHead>
              <TableHead className="sticky top-0 z-20 bg-background font-bold underline">{t("columnDescription")}</TableHead>
              <TableHead className="sticky top-0 z-20 bg-background font-bold underline">{t("columnInfo1")}</TableHead>
              <TableHead className="sticky top-0 z-20 bg-background font-bold underline">{t("columnInfo2")}</TableHead>
              <TableHead className="sticky top-0 z-20 bg-background font-bold underline">{t("columnInfo3")}</TableHead>
              <TableHead className="sticky top-0 right-0 z-30 bg-background text-right font-bold underline">
                {t("tableActions")}
              </TableHead>
            </TableRow>
            {/* The filter row: each control sits directly under the
                column it filters. Actions has no filter, so it gets an
                empty cell to keep alignment exact. */}
            <TableRow>
              <TableHead className="sticky top-10 z-20 bg-background">
                <Input
                  aria-label={t("filterScanner")}
                  placeholder={t("filterScanner")}
                  className="h-8 w-full min-w-32 font-normal"
                  value={scannerFilter}
                  onChange={(event) => setScannerFilter(event.target.value)}
                />
              </TableHead>
              <TableHead className="sticky top-10 z-20 bg-background">
                <Select value={typeFilter} onValueChange={(value) => setTypeFilter(value ?? ALL_VALUE)}>
                  <SelectTrigger aria-label={t("filterType")} className="h-8 w-full font-normal">
                    <SelectValue>
                      {(value: string | null) =>
                        value && value !== ALL_VALUE
                          ? (productTypes.find((productType) => String(productType.id) === value)?.name ??
                            t("allTypes"))
                          : t("allTypes")
                      }
                    </SelectValue>
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value={ALL_VALUE}>{t("allTypes")}</SelectItem>
                    {productTypes.map((productType) => (
                      <SelectItem key={productType.id} value={String(productType.id)}>
                        {productType.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </TableHead>
              <TableHead className="sticky top-10 z-20 bg-background">
                <Select
                  value={technologyFilter}
                  onValueChange={(value) => setTechnologyFilter(value ?? ALL_VALUE)}
                >
                  <SelectTrigger aria-label={t("filterTechnology")} className="h-8 w-full font-normal">
                    <SelectValue>
                      {(value: string | null) => (value && value !== ALL_VALUE ? value : t("allTechnologies"))}
                    </SelectValue>
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value={ALL_VALUE}>{t("allTechnologies")}</SelectItem>
                    {TECHNOLOGY_VALUES.map((technologyValue) => (
                      <SelectItem key={technologyValue} value={technologyValue}>
                        {technologyValue}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </TableHead>
              <TableHead className="sticky top-10 z-20 bg-background">
                <Input
                  aria-label={t("filterLocation")}
                  placeholder={t("filterLocation")}
                  className="h-8 w-full min-w-32 font-normal"
                  value={locationFilter}
                  onChange={(event) => setLocationFilter(event.target.value)}
                />
              </TableHead>
              <TableHead className="sticky top-10 z-20 bg-background">
                <Input
                  aria-label={t("filterDescription")}
                  placeholder={t("filterDescription")}
                  className="h-8 w-full min-w-32 font-normal"
                  value={descriptionFilter}
                  onChange={(event) => setDescriptionFilter(event.target.value)}
                />
              </TableHead>
              <TableHead className="sticky top-10 z-20 bg-background">
                <Input
                  aria-label={t("filterInfo1")}
                  placeholder={t("filterInfo1")}
                  className="h-8 w-full min-w-32 font-normal"
                  value={info1Filter}
                  onChange={(event) => setInfo1Filter(event.target.value)}
                />
              </TableHead>
              <TableHead className="sticky top-10 z-20 bg-background">
                <Input
                  aria-label={t("filterInfo2")}
                  placeholder={t("filterInfo2")}
                  className="h-8 w-full min-w-32 font-normal"
                  value={info2Filter}
                  onChange={(event) => setInfo2Filter(event.target.value)}
                />
              </TableHead>
              <TableHead className="sticky top-10 z-20 bg-background">
                <Input
                  aria-label={t("filterInfo3")}
                  placeholder={t("filterInfo3")}
                  className="h-8 w-full min-w-32 font-normal"
                  value={info3Filter}
                  onChange={(event) => setInfo3Filter(event.target.value)}
                />
              </TableHead>
              <TableHead className="sticky top-10 right-0 z-30 bg-background" />
            </TableRow>
          </TableHeader>
          <TableBody>
            {filteredScanners.map((scanner) => (
              <TableRow key={scanner.id} className="group">
                <TableCell className="font-medium">{scanner.scanner}</TableCell>
                <TableCell className="text-muted-foreground">{typeLabelFor(scanner.type_id)}</TableCell>
                <TableCell className="text-muted-foreground">{scanner.technology}</TableCell>
                <TableCell className="text-muted-foreground">{scanner.location}</TableCell>
                <TableCell className="text-muted-foreground">{scanner.description}</TableCell>
                <TableCell className="text-muted-foreground">{scanner.info1}</TableCell>
                <TableCell className="text-muted-foreground">{scanner.info2}</TableCell>
                <TableCell className="text-muted-foreground">{scanner.info3}</TableCell>
                <TableCell className="sticky right-0 z-10 bg-background group-hover:bg-muted/50">
                  <div className="flex justify-end gap-1">
                    <ScannerApiKeyDialog
                      scanner={scanner}
                      trigger={
                        <Button variant="ghost" size="icon" aria-label={t("apiKey")} title={t("apiKey")}>
                          <KeyRound className="size-4" />
                        </Button>
                      }
                      onChanged={upsert}
                    />
                    <ScannerFormDialog
                      scanner={scanner}
                      trigger={
                        <Button variant="ghost" size="icon" aria-label={t("change")} title={t("change")}>
                          <Pencil className="size-4" />
                        </Button>
                      }
                      onSaved={upsert}
                      productTypes={productTypes}
                    />
                    <DeleteScannerAlertDialog
                      scanner={scanner}
                      onDeleted={(scannerId) => {
                        setScanners((current) => current.filter((item) => item.id !== scannerId));
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

interface ScannerFormDialogProps {
  scanner?: Scanner;
  trigger: React.ReactElement;
  onSaved: (scanner: Scanner) => void;
  productTypes: ProductType[];
}

function ScannerFormDialog({ scanner, trigger, onSaved, productTypes }: ScannerFormDialogProps) {
  const t = useTranslations("tagscan.scanners");
  const isEditing = scanner !== undefined;
  const [isOpen, setIsOpen] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [form, setForm] = useState<ScannerFormState>(scanner ? toFormValues(scanner) : emptyForm(productTypes));

  function handleOpenChange(open: boolean) {
    setIsOpen(open);
    if (open) {
      // Start from the scanner's latest known values each time the
      // dialog is opened, in case they changed since last time.
      setForm(scanner ? toFormValues(scanner) : emptyForm(productTypes));
    }
  }

  function updateField<K extends keyof ScannerFormState>(field: K, value: ScannerFormState[K]) {
    setForm((current) => ({ ...current, [field]: value }));
  }

  async function handleSubmit() {
    if (form.type_id === null) return;
    setIsSubmitting(true);
    try {
      const payload: ScannerInput = { ...form, type_id: form.type_id };
      const savedScanner = isEditing ? await updateScanner(scanner.id, payload) : await createScanner(payload);
      toast.success(isEditing ? t("scannerUpdated") : t("scannerCreated"));
      onSaved(savedScanner);
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
            <Label htmlFor="scanner-name">{t("scannerLabel")}</Label>
            <Input
              id="scanner-name"
              value={form.scanner}
              onChange={(event) => updateField("scanner", event.target.value)}
            />
          </div>

          <div className="flex flex-col gap-2">
            <Label htmlFor="scanner-type">{t("typeLabel")}</Label>
            <Select
              value={form.type_id !== null ? String(form.type_id) : ""}
              onValueChange={(value) => updateField("type_id", value ? Number(value) : null)}
            >
              <SelectTrigger id="scanner-type">
                <SelectValue>
                  {(value: string | null) => productTypes.find((productType) => String(productType.id) === value)?.name ?? ""}
                </SelectValue>
              </SelectTrigger>
              <SelectContent>
                {productTypes.map((productType) => (
                  <SelectItem key={productType.id} value={String(productType.id)}>
                    {productType.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="flex flex-col gap-2">
            <Label htmlFor="scanner-technology">{t("technologyLabel")}</Label>
            <Select
              value={form.technology}
              onValueChange={(value) => updateField("technology", (value ?? "Other") as ScannerTechnology)}
            >
              <SelectTrigger id="scanner-technology">
                <SelectValue>{(value: string | null) => value ?? ""}</SelectValue>
              </SelectTrigger>
              <SelectContent>
                {TECHNOLOGY_VALUES.map((technologyValue) => (
                  <SelectItem key={technologyValue} value={technologyValue}>
                    {technologyValue}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="col-span-2 flex flex-col gap-2">
            <Label htmlFor="scanner-location">{t("locationLabel")}</Label>
            <Input
              id="scanner-location"
              value={form.location ?? ""}
              onChange={(event) => updateField("location", event.target.value)}
            />
          </div>

          <div className="col-span-2 flex flex-col gap-2">
            <Label htmlFor="scanner-description">{t("descriptionLabel")}</Label>
            <Textarea
              id="scanner-description"
              value={form.description ?? ""}
              onChange={(event) => updateField("description", event.target.value)}
            />
          </div>

          <div className="col-span-2 flex flex-col gap-2">
            <Label htmlFor="scanner-info1">{t("info1Label")}</Label>
            <Input
              id="scanner-info1"
              value={form.info1 ?? ""}
              onChange={(event) => updateField("info1", event.target.value)}
            />
          </div>
          <div className="col-span-2 flex flex-col gap-2">
            <Label htmlFor="scanner-info2">{t("info2Label")}</Label>
            <Input
              id="scanner-info2"
              value={form.info2 ?? ""}
              onChange={(event) => updateField("info2", event.target.value)}
            />
          </div>
          <div className="col-span-2 flex flex-col gap-2">
            <Label htmlFor="scanner-info3">{t("info3Label")}</Label>
            <Input
              id="scanner-info3"
              value={form.info3 ?? ""}
              onChange={(event) => updateField("info3", event.target.value)}
            />
          </div>
        </div>

        <DialogFooter>
          <Button onClick={handleSubmit} disabled={isSubmitting || !form.scanner || form.type_id === null}>
            {isEditing ? t("change") : t("newScanner")}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

interface ScannerApiKeyDialogProps {
  scanner: Scanner;
  trigger: React.ReactElement;
  onChanged: (scanner: Scanner) => void;
}

/** Generate/revoke a scanner's device CSV-intake API key — see
 * app/modules/module_1/device_router.py on the backend. A freshly
 * generated key is only ever shown here, once; after the dialog closes
 * it can never be retrieved again, only replaced with a new one. */
function ScannerApiKeyDialog({ scanner, trigger, onChanged }: ScannerApiKeyDialogProps) {
  const t = useTranslations("tagscan.scanners");
  const [isOpen, setIsOpen] = useState(false);
  const [isBusy, setIsBusy] = useState(false);
  const [revealedKey, setRevealedKey] = useState<string | null>(null);

  function handleOpenChange(open: boolean) {
    setIsOpen(open);
    if (open) setRevealedKey(null);
  }

  async function handleGenerate() {
    setIsBusy(true);
    try {
      const { api_key } = await generateScannerApiKey(scanner.id);
      setRevealedKey(api_key);
      onChanged({ ...scanner, has_api_key: true, api_key_last_used_at: null });
    } catch (error) {
      toast.error(error instanceof ApiError ? error.message : t("apiKeyGenerateFailed"));
    } finally {
      setIsBusy(false);
    }
  }

  async function handleRevoke() {
    setIsBusy(true);
    try {
      await revokeScannerApiKey(scanner.id);
      setRevealedKey(null);
      onChanged({ ...scanner, has_api_key: false, api_key_last_used_at: null });
      toast.success(t("apiKeyRevoked"));
    } catch (error) {
      toast.error(error instanceof ApiError ? error.message : t("apiKeyRevokeFailed"));
    } finally {
      setIsBusy(false);
    }
  }

  return (
    <Dialog open={isOpen} onOpenChange={handleOpenChange}>
      <DialogTrigger render={trigger} />
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>{t("apiKeyTitle", { scanner: scanner.scanner })}</DialogTitle>
          <DialogDescription>{t("apiKeyDescription")}</DialogDescription>
        </DialogHeader>

        <div className="flex flex-col gap-4">
          {revealedKey ? (
            <div className="flex flex-col gap-2">
              <Label>{t("apiKeyNewValue")}</Label>
              <div className="flex gap-2">
                <Input readOnly value={revealedKey} className="font-mono text-sm" />
                <Button
                  type="button"
                  variant="outline"
                  onClick={() =>
                    copyToClipboard(
                      revealedKey,
                      () => toast.success(t("copied")),
                      () => toast.error(t("copyFailed")),
                    )
                  }
                >
                  {t("copy")}
                </Button>
              </div>
              <p className="text-sm text-destructive">{t("apiKeyShownOnceWarning")}</p>
            </div>
          ) : (
            <div className="flex items-center gap-2">
              <Badge variant={scanner.has_api_key ? "default" : "secondary"}>
                {scanner.has_api_key ? t("apiKeyActive") : t("apiKeyNone")}
              </Badge>
              {scanner.has_api_key && (
                <span className="text-sm text-muted-foreground">
                  {scanner.api_key_last_used_at
                    ? t("apiKeyLastUsed", { date: new Date(scanner.api_key_last_used_at).toLocaleString() })
                    : t("apiKeyNeverUsed")}
                </span>
              )}
            </div>
          )}

          <div className="flex flex-col gap-2">
            <Label>{t("apiKeyUploadUrl")}</Label>
            <div className="flex gap-2">
              <Input readOnly value={INTAKE_UPLOAD_URL} className="font-mono text-sm" />
              <Button
                type="button"
                variant="outline"
                onClick={() =>
                  copyToClipboard(
                    INTAKE_UPLOAD_URL,
                    () => toast.success(t("copied")),
                    () => toast.error(t("copyFailed")),
                  )
                }
              >
                {t("copy")}
              </Button>
            </div>
          </div>
        </div>

        <DialogFooter className="gap-2 sm:justify-between">
          {scanner.has_api_key && (
            <Button type="button" variant="destructive" disabled={isBusy} onClick={handleRevoke}>
              {t("apiKeyRevoke")}
            </Button>
          )}
          <Button type="button" disabled={isBusy} onClick={handleGenerate}>
            {scanner.has_api_key ? t("apiKeyRegenerate") : t("apiKeyGenerate")}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

interface DeleteScannerAlertDialogProps {
  scanner: Scanner;
  onDeleted: (scannerId: number) => void;
}

function DeleteScannerAlertDialog({ scanner, onDeleted }: DeleteScannerAlertDialogProps) {
  const t = useTranslations("tagscan.scanners");
  const tCommon = useTranslations("common");
  const [isOpen, setIsOpen] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);

  async function handleConfirmDelete() {
    setIsDeleting(true);
    try {
      await deleteScanner(scanner.id);
      toast.success(t("scannerDeleted"));
      onDeleted(scanner.id);
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
            {t("deleteConfirmDescription", { scanner: scanner.scanner })}
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
