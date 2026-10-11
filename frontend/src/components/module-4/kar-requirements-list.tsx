"use client";

// One kar's needs for one season ("Benodigdheden"), as an editable list:
// add products with the same basket-style input as the booking panel
// (search, Enter, quantity, Enter), change quantities/comments, remove
// lines, fill it from the Inboeken Excel, copy last season's lines of the
// same kar (only adds/updates, never removes), open the Laadlijst PDF and
// save. Used by StockMaster's own "Benodigdheden" screen and by Altsien
// Select's Products wizard step; each passes its own `api` (its own
// endpoints and rights), the list itself is the same.

import { useEffect, useMemo, useRef, useState } from "react";
import { Copy, FileSpreadsheet, FileText, Trash2, Upload, X } from "lucide-react";
import { useLocale, useTranslations } from "next-intl";
import { toast } from "sonner";
import type {
  StockMasterBookInImport,
  StockMasterPreviousRequirements,
  StockMasterProductStock,
  StockMasterRequirement,
  StockMasterRequirementInput,
} from "@/lib/types";
import { cn } from "@/lib/utils";
import { Button, buttonVariants } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { ProductThumb } from "@/components/module-4/product-thumb";
import { ProductSearch } from "@/components/module-4/stock-pickers";
import { stockErrorMessage } from "@/components/module-4/stockmaster-common";

/** Where the list reads and stores its data — StockMaster's own endpoints,
 *  or the Altsien Select wizard's. Keep the object stable (module constant
 *  or useMemo), since the list reloads when it changes. */
export interface KarRequirementsApi {
  loadStock: () => Promise<StockMasterProductStock[]>;
  loadRequirements: (seasonId: number, karId: number) => Promise<StockMasterRequirement[]>;
  loadPrevious: (seasonId: number, karId: number) => Promise<StockMasterPreviousRequirements>;
  save: (seasonId: number, karId: number, lines: StockMasterRequirementInput[]) => Promise<StockMasterRequirement[]>;
  importExcel: (file: File) => Promise<StockMasterBookInImport>;
  templateUrl: string;
  loadListPdfUrl: (karId: number, seasonId: number, locale: string) => string;
  productImageUrl: (productId: number, updatedAt: string | null) => string;
}

/** Stores the pending list; resolves false when that failed. */
export type KarRequirementsSaver = () => Promise<boolean>;

interface KarRequirementsListProps {
  api: KarRequirementsApi;
  seasonId: number;
  karId: number;
  /** Nothing can be changed (closed season, or no rights at all). */
  readOnly: boolean;
  canCreate: boolean;
  canEdit: boolean;
  canDelete: boolean;
  /** False when the parent stores the list itself (via registerSave). */
  showSaveButton?: boolean;
  onDirtyChange?: (dirty: boolean) => void;
  /** Hands the parent a saver for the pending list (null on unmount). */
  registerSave?: (saver: KarRequirementsSaver | null) => void;
  /** Called (and awaited) after a successful save. */
  onSaved?: () => Promise<void> | void;
}

/** One line being edited. */
interface EditLine {
  productId: number;
  name: string;
  binLabel: string | null;
  quantity: number;
  comment: string;
  inKar: number;
  /** Already stored (so changing/removing it needs edit/delete rights). */
  stored: boolean;
}

export function KarRequirementsList({
  api,
  seasonId,
  karId,
  readOnly,
  canCreate,
  canEdit,
  canDelete,
  showSaveButton = true,
  onDirtyChange,
  registerSave,
  onSaved,
}: KarRequirementsListProps) {
  const t = useTranslations("stockMaster");
  const tReq = useTranslations("stockMaster.requirements");
  const locale = useLocale();

  const [stock, setStock] = useState<StockMasterProductStock[]>([]);
  // The list being edited and last season's list, each stored with the
  // "season:kar" they belong to, so a list never shows (or gets saved) under
  // another kar while the next one is loading.
  const [edit, setEdit] = useState<{ key: string; lines: EditLine[] } | null>(null);
  const [isDirty, setIsDirty] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [previousState, setPreviousState] = useState<{ key: string; data: StockMasterPreviousRequirements } | null>(null);
  const [pickedPrevious, setPickedPrevious] = useState<Set<number>>(new Set());
  const [pendingProduct, setPendingProduct] = useState<StockMasterProductStock | null>(null);
  const [pendingQuantity, setPendingQuantity] = useState("1");
  const searchRef = useRef<HTMLInputElement>(null);
  const quantityRef = useRef<HTMLInputElement>(null);
  // Excel upload: the hidden file input, its busy flag and the rows it couldn't use.
  const importInputRef = useRef<HTMLInputElement>(null);
  const [isImporting, setIsImporting] = useState(false);
  const [importErrors, setImportErrors] = useState<StockMasterBookInImport["errors"]>([]);

  useEffect(() => {
    api
      .loadStock()
      .then(setStock)
      .catch(() => toast.error(t("errors.loadFailed")));
  }, [api, t]);

  // Stock rows by product id, for each line's picture.
  const productsById = useMemo(() => new Map(stock.map((product) => [product.product_id, product])), [stock]);

  const currentKey = `${seasonId}:${karId}`;
  const lines = edit !== null && edit.key === currentKey ? edit.lines : null;
  const previous = previousState !== null && previousState.key === currentKey ? previousState.data : null;

  // Load the kar's list (and last season's, for the copy panel).
  useEffect(() => {
    const key = `${seasonId}:${karId}`;
    api
      .loadRequirements(seasonId, karId)
      .then((rows) => {
        setEdit({ key, lines: rows.map(toEditLine) });
        setIsDirty(false);
      })
      .catch((error) => toast.error(stockErrorMessage(t, error)));
    api
      .loadPrevious(seasonId, karId)
      .then((result) => {
        setPreviousState({ key, data: result });
        setPickedPrevious(new Set(result.lines.map((line) => line.product_id)));
      })
      .catch(() => undefined);
  }, [api, seasonId, karId, t]);

  // Tell the parent when the list has unsaved changes (e.g. to confirm a kar switch).
  useEffect(() => {
    onDirtyChange?.(isDirty);
  }, [isDirty, onDirtyChange]);

  function change(updater: (current: EditLine[]) => EditLine[]) {
    setEdit((current) => (current !== null && current.key === currentKey ? { key: current.key, lines: updater(current.lines) } : current));
    setIsDirty(true);
  }

  function addPending() {
    if (!pendingProduct) return;
    const quantity = Number.parseInt(pendingQuantity, 10);
    if (!Number.isFinite(quantity) || quantity < 1) {
      toast.error(t("booking.quantityTooLow"));
      return;
    }
    const product = pendingProduct;
    change((current) => {
      const existing = current.find((line) => line.productId === product.product_id);
      if (existing) {
        return current.map((line) => (line === existing ? { ...line, quantity: line.quantity + quantity } : line));
      }
      const inKar = product.kars.find((kar) => kar.kar_id === karId)?.quantity ?? 0;
      return [
        ...current,
        { productId: product.product_id, name: product.name, binLabel: product.bin_label, quantity, comment: "", inKar, stored: false },
      ];
    });
    setPendingProduct(null);
    setPendingQuantity("1");
    window.setTimeout(() => searchRef.current?.focus(), 0);
  }

  /** Copy the ticked lines of last season (adds or updates, never removes). */
  function copyPrevious() {
    if (!previous) return;
    change((current) => {
      const next = [...current];
      for (const line of previous.lines) {
        if (!pickedPrevious.has(line.product_id)) continue;
        const existing = next.findIndex((item) => item.productId === line.product_id);
        if (existing >= 0) {
          next[existing] = { ...next[existing], quantity: line.quantity };
        } else {
          const product = productsById.get(line.product_id);
          next.push({
            productId: line.product_id,
            name: line.product_name,
            binLabel: product?.bin_label ?? null,
            quantity: line.quantity,
            comment: "",
            inKar: product?.kars.find((kar) => kar.kar_id === karId)?.quantity ?? 0,
            stored: false,
          });
        }
      }
      return next;
    });
    toast.success(tReq("copied"));
  }

  /** Fill the list from an uploaded Excel (the Inboeken template): a product
   *  already in the list gets the file's quantity, a new one is added. Never
   *  removes lines and stores nothing until Save. Lines the user may not
   *  change (stored line without edit right, new line without create right)
   *  are left alone. */
  async function importExcel(file: File) {
    setIsImporting(true);
    try {
      const result = await api.importExcel(file);
      // Whether the user may apply a file row to the list as it is now.
      const allowed = (current: EditLine[], productId: number) => {
        const existing = current.find((line) => line.productId === productId);
        return existing ? !existing.stored || canEdit : canCreate;
      };
      const skipped = result.lines.filter((row) => !allowed(lines ?? [], row.product_id)).length;
      change((current) => {
        const next = [...current];
        for (const row of result.lines) {
          if (!allowed(next, row.product_id)) continue;
          const existing = next.findIndex((line) => line.productId === row.product_id);
          if (existing >= 0) {
            next[existing] = { ...next[existing], quantity: row.quantity };
          } else {
            const product = productsById.get(row.product_id);
            next.push({
              productId: row.product_id,
              name: product?.name ?? `#${row.product_id}`,
              binLabel: product?.bin_label ?? null,
              quantity: row.quantity,
              comment: "",
              inKar: product?.kars.find((kar) => kar.kar_id === karId)?.quantity ?? 0,
              stored: false,
            });
          }
        }
        return next;
      });
      setImportErrors(result.errors);
      if (result.lines.length > 0) toast.success(t("booking.importAdded", { count: result.lines.length - skipped }));
      else toast.info(t("booking.importAdded", { count: 0 }));
      if (skipped > 0) toast.warning(tReq("importSkipped", { count: skipped }));
    } catch (error) {
      toast.error(stockErrorMessage(t, error));
    } finally {
      setIsImporting(false);
    }
  }

  /** One problem row of the upload as readable text ("code|param" → translation). */
  function importErrorText(detail: string): string {
    const [code, param = ""] = detail.split("|");
    return t.has(`booking.importErrors.${code}`) ? t(`booking.importErrors.${code}`, { p1: param }) : detail;
  }

  const invalid = (lines ?? []).some((line) => !Number.isInteger(line.quantity) || line.quantity < 1);

  /** Store the list; false when that failed (or a quantity is invalid). */
  async function save(): Promise<boolean> {
    if (!lines) return true;
    if (invalid) {
      toast.error(t("booking.quantityTooLow"));
      return false;
    }
    setIsSaving(true);
    try {
      const rows = await api.save(
        seasonId,
        karId,
        lines.map((line) => ({ product_id: line.productId, quantity: line.quantity, comment: line.comment.trim() || null })),
      );
      setEdit({ key: `${seasonId}:${karId}`, lines: rows.map(toEditLine) });
      setIsDirty(false);
      toast.success(tReq("saved"));
      await onSaved?.();
      return true;
    } catch (error) {
      toast.error(stockErrorMessage(t, error));
      return false;
    } finally {
      setIsSaving(false);
    }
  }

  // Offer the parent a saver for the pending list (only stores when something changed).
  useEffect(() => {
    if (!registerSave) return;
    registerSave(async () => (!isDirty || readOnly ? true : save()));
    return () => registerSave(null);
  });

  const total = (lines ?? []).reduce((sum, line) => sum + line.quantity, 0);
  // Last season's copy panel is the only thing in the right column; without it the list takes the full width.
  const showPrevious = !readOnly && previous !== null && previous.lines.length > 0;

  if (lines === null) {
    return <p className="text-sm text-muted-foreground">{t("common.loading")}</p>;
  }

  return (
    <div
      className={cn("grid gap-6", showPrevious && "lg:grid-cols-[minmax(0,1fr)_20rem]")}
      onKeyDown={(event) => {
        if (event.key === "Enter" && (event.ctrlKey || event.metaKey)) {
          event.preventDefault();
          if (isDirty && !invalid && !readOnly) void save();
        }
      }}
    >
      <div className="flex flex-col gap-4">
        {!readOnly && canCreate && (
          <div className="flex flex-wrap items-end gap-3">
            <div className="flex min-w-64 flex-1 flex-col gap-2">
              <Label htmlFor="req-product">{t("booking.productLabel")}</Label>
              {pendingProduct ? (
                <div className="flex h-8 items-center gap-2 rounded-md border bg-muted/40 px-3 text-sm">
                  <span className="font-medium">{pendingProduct.name}</span>
                  <button type="button" className="ml-auto text-xs text-muted-foreground underline" onClick={() => setPendingProduct(null)}>
                    {t("booking.otherProduct")}
                  </button>
                </div>
              ) : (
                <ProductSearch
                  id="req-product"
                  ref={searchRef}
                  products={stock}
                  onSelect={(product) => {
                    setPendingProduct(product);
                    window.setTimeout(() => quantityRef.current?.select(), 0);
                  }}
                />
              )}
            </div>
            <div className="flex w-28 flex-col gap-2">
              <Label htmlFor="req-quantity">{t("booking.quantityLabel")}</Label>
              <Input
                id="req-quantity"
                ref={quantityRef}
                type="number"
                min={1}
                step={1}
                inputMode="numeric"
                disabled={!pendingProduct}
                value={pendingQuantity}
                onChange={(event) => setPendingQuantity(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === "Enter" && !event.ctrlKey && !event.metaKey) {
                    event.preventDefault();
                    addPending();
                  }
                }}
              />
            </div>
            <Button variant="outline" onClick={addPending} disabled={!pendingProduct}>
              {t("booking.addLine")}
            </Button>
          </div>
        )}

        {/* From Excel: download the template, upload it filled in → the list below (still to be saved). */}
        {!readOnly && (canCreate || canEdit) && (
          <div className="flex flex-col gap-2">
            <div className="flex flex-wrap items-center gap-2">
              <a href={api.templateUrl} download className={buttonVariants({ variant: "outline", size: "sm" })}>
                <FileSpreadsheet />
                {t("booking.importTemplate")}
              </a>
              <Button variant="outline" size="sm" onClick={() => importInputRef.current?.click()} disabled={isImporting}>
                <Upload />
                {t("booking.importUpload")}
              </Button>
              <input
                ref={importInputRef}
                type="file"
                accept=".xlsx,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                className="hidden"
                onChange={(event) => {
                  const file = event.target.files?.[0];
                  // Cleared right away so the same file can be uploaded again after fixing it.
                  event.target.value = "";
                  if (file) void importExcel(file);
                }}
              />
            </div>
            <p className="text-xs text-muted-foreground">{tReq("importHint")}</p>
            {/* Rows of the file that couldn't be used, until closed. */}
            {importErrors.length > 0 && (
              <div className="rounded-md border border-destructive/40 bg-destructive/10 px-3 py-2 text-sm text-destructive">
                <div className="flex items-start justify-between gap-2">
                  <span className="font-semibold">{t("booking.importErrorsTitle")}</span>
                  <button type="button" onClick={() => setImportErrors([])} aria-label={t("booking.importClose")}>
                    <X className="size-4" />
                  </button>
                </div>
                <ul className="mt-1 list-disc pl-5">
                  {importErrors.map((error) => (
                    <li key={`${error.row_number}-${error.detail}`}>
                      {t("booking.importErrorRow", { row: error.row_number, message: importErrorText(error.detail) })}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}

        {lines.length === 0 ? (
          <p className="rounded-md border border-dashed px-4 py-6 text-center text-sm text-muted-foreground">{tReq("empty")}</p>
        ) : (
          <div className="rounded-md border [&>div]:max-h-[65vh] [&>div]:overflow-y-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="sticky top-0 z-20 bg-background font-bold underline">{t("common.product")}</TableHead>
                  <TableHead className="sticky top-0 z-20 bg-background font-bold underline">{t("common.bin")}</TableHead>
                  <TableHead className="sticky top-0 z-20 w-28 bg-background font-bold underline">{tReq("quantity")}</TableHead>
                  <TableHead className="sticky top-0 z-20 bg-background font-bold underline">{tReq("comment")}</TableHead>
                  <TableHead className="sticky top-0 z-20 bg-background text-right font-bold underline">{t("kars.inKar")}</TableHead>
                  <TableHead className="sticky top-0 right-0 z-30 w-12 bg-background text-right font-bold underline">
                    <span className="sr-only">{t("common.actions")}</span>
                  </TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {lines.map((line) => {
                  const editable = !readOnly && (line.stored ? canEdit : canCreate);
                  return (
                    <TableRow key={line.productId} className="group">
                      {/* The product's picture (or placeholder icon) next to its name. */}
                      <TableCell className="font-medium">
                        <div className="flex items-center gap-3">
                          <ProductThumb
                            productId={line.productId}
                            name={line.name}
                            product={productsById.get(line.productId)}
                            imageUrl={api.productImageUrl}
                          />
                          <span>{line.name}</span>
                        </div>
                      </TableCell>
                      <TableCell className="text-muted-foreground">{line.binLabel ?? t("common.noBin")}</TableCell>
                      <TableCell>
                        <Input
                          type="number"
                          min={1}
                          step={1}
                          inputMode="numeric"
                          aria-label={tReq("quantity")}
                          className="w-24"
                          disabled={!editable}
                          value={line.quantity}
                          onChange={(event) =>
                            change((current) =>
                              current.map((item) =>
                                item.productId === line.productId
                                  ? { ...item, quantity: Number.parseInt(event.target.value, 10) || 0 }
                                  : item,
                              ),
                            )
                          }
                        />
                      </TableCell>
                      <TableCell>
                        <Input
                          aria-label={tReq("comment")}
                          disabled={!editable}
                          value={line.comment}
                          onChange={(event) =>
                            change((current) =>
                              current.map((item) =>
                                item.productId === line.productId ? { ...item, comment: event.target.value } : item,
                              ),
                            )
                          }
                        />
                      </TableCell>
                      <TableCell
                        className={cn(
                          "text-right tabular-nums",
                          line.inKar >= line.quantity ? "text-green-700 dark:text-green-400" : "text-orange-700 dark:text-orange-300",
                        )}
                      >
                        {line.inKar}
                      </TableCell>
                      <TableCell className="sticky right-0 z-10 bg-background text-right group-hover:bg-muted/50">
                        {!readOnly && (line.stored ? canDelete : true) && (
                          <Button
                            variant="ghost"
                            size="icon-sm"
                            aria-label={t("booking.removeLine")}
                            onClick={() => change((current) => current.filter((item) => item.productId !== line.productId))}
                          >
                            <Trash2 />
                          </Button>
                        )}
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          </div>
        )}

        {/* Action bar under the list: totals and the unsaved notice on the left, Laadlijst PDF and
            Save on the right. */}
        <div className="flex flex-wrap items-center gap-3">
          <p className="text-sm text-muted-foreground">{t("booking.summary", { products: lines.length, pieces: total })}</p>
          {isDirty && <p className="text-xs text-orange-700 dark:text-orange-300">{tReq("unsaved")}</p>}
          <div className="ml-auto flex flex-wrap gap-2">
            <a
              href={api.loadListPdfUrl(karId, seasonId, locale)}
              target="_blank"
              rel="noreferrer"
              className={buttonVariants({ variant: "outline" })}
            >
              <FileText />
              {t("kars.loadList")}
            </a>
            {!readOnly && showSaveButton && (
              <Button onClick={() => void save()} disabled={!isDirty || invalid || isSaving}>
                {tReq("save")}
              </Button>
            )}
          </div>
        </div>
      </div>

      {/* Right column: only last season's lines to copy, when there are any. */}
      {showPrevious && previous && (
        <div className="flex flex-col gap-4">
          <Card>
            <CardContent className="flex flex-col gap-3 text-sm">
              <span className="font-semibold">{tReq("previousTitle", { season: previous.season_name ?? "" })}</span>
              <div className="flex items-center gap-2">
                <Checkbox
                  id="req-previous-all"
                  checked={pickedPrevious.size === previous.lines.length}
                  onCheckedChange={(checked) =>
                    setPickedPrevious(checked === true ? new Set(previous.lines.map((line) => line.product_id)) : new Set())
                  }
                />
                <Label htmlFor="req-previous-all">{tReq("selectAll")}</Label>
              </div>
              <ul className="flex max-h-64 flex-col gap-1 overflow-y-auto">
                {previous.lines.map((line) => (
                  <li key={line.product_id} className="flex items-center gap-2">
                    <Checkbox
                      id={`req-previous-${line.product_id}`}
                      checked={pickedPrevious.has(line.product_id)}
                      onCheckedChange={(checked) =>
                        setPickedPrevious((current) => {
                          const next = new Set(current);
                          if (checked === true) next.add(line.product_id);
                          else next.delete(line.product_id);
                          return next;
                        })
                      }
                    />
                    <Label htmlFor={`req-previous-${line.product_id}`} className="flex-1 font-normal">
                      {line.product_name}
                    </Label>
                    <span className="tabular-nums">{line.quantity}</span>
                    {line.current_quantity !== null && (
                      <span className="text-xs text-muted-foreground">({tReq("now", { count: line.current_quantity })})</span>
                    )}
                  </li>
                ))}
              </ul>
              <Button variant="outline" onClick={copyPrevious} disabled={pickedPrevious.size === 0}>
                <Copy />
                {tReq("copy")}
              </Button>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}

/** A stored need as an editable line. */
function toEditLine(row: StockMasterRequirement): EditLine {
  return {
    productId: row.product_id,
    name: row.product_name,
    binLabel: row.bin_label,
    quantity: row.quantity,
    comment: row.comment ?? "",
    inKar: row.in_kar,
    stored: true,
  };
}
