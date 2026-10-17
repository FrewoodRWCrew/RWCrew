"use client";

// MasterData's "Products" screen: a table of products with add/change/
// delete, following the same dialog/table pattern as season-management.tsx
// — the create/edit dialog covers every field from the reference
// "Producten" screen, including the product's picture (chosen with a file
// button, uploaded right after the fields are saved).

import { useEffect, useState } from "react";
import { ImageOff, Info, Pencil, Trash2 } from "lucide-react";
import { useTranslations } from "next-intl";
import { useSearchParams } from "next/navigation";
import { toast } from "sonner";
import { useRouter } from "@/i18n/navigation";
import {
  ApiError,
  createProduct,
  deleteProduct,
  deleteProductImage,
  productImageUrl,
  updateProduct,
  uploadProductImage,
} from "@/lib/api";
import type { Product, ProductCategory, ProductInput, ProductLimit, ProductType, Warehouse } from "@/lib/types";
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
import { Textarea } from "@/components/ui/textarea";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";

interface ProductsManagementProps {
  initialProducts: Product[];
  productTypes: ProductType[];
  warehouses: Warehouse[];
  productCategories: ProductCategory[];
  productLimits: ProductLimit[];
}

// Base UI's Select needs every item to have a non-empty value, so "no
// selection" is represented by this sentinel string instead of "".
const NO_SELECTION_VALUE = "none";
// The Limiet (matched by name, ignoring case) whose Limietwaarde is required — same rule as the backend.
const PERCENTAGE_LIMIT_NAME = "percentage";

// The picture types the backend accepts (it also refuses anything over 5 MB).
const ACCEPTED_IMAGE_TYPES = "image/png,image/jpeg,image/webp";
const MAX_IMAGE_BYTES = 5 * 1024 * 1024;

const EMPTY_FORM: ProductInput = {
  name: "",
  type_id: null,
  warehouse_id: null,
  warehouse_location: "",
  category_id: null,
  is_consumable: false,
  is_blocked: false,
  is_logistics_product: false,
  is_tag_managed: false,
  limit_id: null,
  limit_value: null,
  max_initial_stock: null,
  description: "",
  cost: null,
  stock_return_to: "kar",
  min_stock: null,
};

function toFormValues(product: Product): ProductInput {
  return {
    name: product.name,
    type_id: product.type_id,
    warehouse_id: product.warehouse_id,
    warehouse_location: product.warehouse_location ?? "",
    category_id: product.category_id,
    is_consumable: product.is_consumable,
    is_blocked: product.is_blocked,
    is_logistics_product: product.is_logistics_product,
    is_tag_managed: product.is_tag_managed,
    limit_id: product.limit_id,
    limit_value: product.limit_value,
    max_initial_stock: product.max_initial_stock,
    description: product.description ?? "",
    cost: product.cost,
    stock_return_to: product.stock_return_to,
    min_stock: product.min_stock,
  };
}

export function ProductsManagement({
  initialProducts,
  productTypes,
  warehouses,
  productCategories,
  productLimits,
}: ProductsManagementProps) {
  const t = useTranslations("masterdata.products");
  const router = useRouter();

  const [products, setProducts] = useState(initialProducts);
  // Arriving from a link to one product (?product=<id>, e.g. from TagScan's
  // Tag Linedata): that product's fiche opens straight away.
  const linkedProductId = Number(useSearchParams().get("product")) || null;

  function typeLabelFor(typeId: number | null) {
    return productTypes.find((productType) => productType.id === typeId)?.name ?? "";
  }

  function warehouseLabelFor(warehouseId: number | null) {
    return warehouses.find((warehouse) => warehouse.id === warehouseId)?.name ?? "";
  }

  function categoryLabelFor(categoryId: number | null) {
    return productCategories.find((productCategory) => productCategory.id === categoryId)?.name ?? "";
  }

  function upsert(updated: Product) {
    setProducts((current) => {
      const exists = current.some((product) => product.id === updated.id);
      return exists
        ? current.map((product) => (product.id === updated.id ? updated : product))
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
        <ProductFormDialog
          trigger={<Button>{t("newProduct")}</Button>}
          onSaved={upsert}
          productTypes={productTypes}
          warehouses={warehouses}
          productCategories={productCategories}
          productLimits={productLimits}
        />
      </div>

      <div className="rounded-md border [&>div]:max-h-[65vh] [&>div]:overflow-y-auto">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="sticky top-0 z-20 w-16 bg-background text-center font-bold underline">
                {t("columnImage")}
              </TableHead>
              <TableHead className="sticky top-0 z-20 bg-background font-bold underline">{t("columnName")}</TableHead>
              <TableHead className="sticky top-0 z-20 bg-background font-bold underline">{t("columnType")}</TableHead>
              <TableHead className="sticky top-0 z-20 bg-background font-bold underline">{t("columnWarehouse")}</TableHead>
              <TableHead className="sticky top-0 z-20 bg-background font-bold underline">{t("columnCategory")}</TableHead>
              <TableHead className="sticky top-0 right-0 z-30 bg-background text-right font-bold underline">
                {t("tableActions")}
              </TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {products.map((product) => (
              <TableRow key={product.id} className="group">
                <TableCell>
                  {product.has_image && (
                    // A plain <img> is needed here: the source is a same-site
                    // backend URL, not a Next-optimizable asset.
                    // eslint-disable-next-line @next/next/no-img-element
                    <img
                      src={productImageUrl(product.id, product.image_updated_at)}
                      alt={product.name}
                      loading="lazy"
                      className="mx-auto size-10 rounded border object-contain"
                    />
                  )}
                </TableCell>
                <TableCell className="font-medium">{product.name}</TableCell>
                <TableCell className="text-muted-foreground">{typeLabelFor(product.type_id)}</TableCell>
                <TableCell className="text-muted-foreground">{warehouseLabelFor(product.warehouse_id)}</TableCell>
                <TableCell className="text-muted-foreground">{categoryLabelFor(product.category_id)}</TableCell>
                <TableCell className="sticky right-0 z-10 bg-background group-hover:bg-muted/50">
                  <div className="flex justify-end gap-1">
                    <ProductFormDialog
                      product={product}
                      defaultOpen={product.id === linkedProductId}
                      trigger={
                        <Button variant="ghost" size="icon" aria-label={t("change")} title={t("change")}>
                          <Pencil className="size-4" />
                        </Button>
                      }
                      onSaved={upsert}
                      productTypes={productTypes}
                      warehouses={warehouses}
                      productCategories={productCategories}
                      productLimits={productLimits}
                    />
                    <DeleteProductAlertDialog
                      product={product}
                      onDeleted={(productId) => {
                        setProducts((current) => current.filter((item) => item.id !== productId));
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

interface ProductFormDialogProps {
  product?: Product;
  /** Start opened — when the screen was reached through a link to this product. */
  defaultOpen?: boolean;
  trigger: React.ReactElement;
  onSaved: (product: Product) => void;
  productTypes: ProductType[];
  warehouses: Warehouse[];
  productCategories: ProductCategory[];
  productLimits: ProductLimit[];
}

function ProductFormDialog({
  product,
  defaultOpen,
  trigger,
  onSaved,
  productTypes,
  warehouses,
  productCategories,
  productLimits,
}: ProductFormDialogProps) {
  const t = useTranslations("masterdata.products");
  const isEditing = product !== undefined;
  const [isOpen, setIsOpen] = useState(defaultOpen ?? false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [form, setForm] = useState<ProductInput>(product ? toFormValues(product) : EMPTY_FORM);
  // The picture picked with the file button (not uploaded until "save"),
  // and whether the current picture should be removed on save.
  const [image, setImage] = useState<File | null>(null);
  const [removeImage, setRemoveImage] = useState(false);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  // Remounts the file input so it is emptied after "remove" or reopening.
  const [fileInputKey, setFileInputKey] = useState(0);

  // Free a local preview again once it's replaced or the dialog unmounts.
  useEffect(() => {
    return () => {
      if (previewUrl) URL.revokeObjectURL(previewUrl);
    };
  }, [previewUrl]);

  // The picture shown in the dialog: the picked file, else the saved one (unless marked for removal).
  const displayedImageUrl =
    previewUrl ?? (product?.has_image && !removeImage ? productImageUrl(product.id, product.image_updated_at) : null);

  // Remember the picked file (or none) together with its local preview.
  function pickImage(file: File | null) {
    setImage(file);
    setPreviewUrl(file ? URL.createObjectURL(file) : null);
  }

  function resetImage() {
    pickImage(null);
    setRemoveImage(false);
    setFileInputKey((key) => key + 1);
  }

  function handleOpenChange(open: boolean) {
    setIsOpen(open);
    if (open) {
      // Start from the product's latest known values each time the
      // dialog is opened, in case they changed since last time.
      setForm(product ? toFormValues(product) : EMPTY_FORM);
      resetImage();
    }
  }

  function handleImagePicked(file: File | null) {
    // Refuse a too-large file right away instead of after saving.
    if (file && file.size > MAX_IMAGE_BYTES) {
      toast.error(t("imageTooLarge"));
      setFileInputKey((key) => key + 1);
      return;
    }
    pickImage(file);
    if (file) setRemoveImage(false);
  }

  function handleRemoveImage() {
    pickImage(null);
    setRemoveImage(true);
    setFileInputKey((key) => key + 1);
  }

  // Name of the chosen Limiet, shown in the Limietwaarde's label.
  const selectedLimitName = productLimits.find((productLimit) => productLimit.id === form.limit_id)?.name;
  // The "Percentage" Limiet needs its Limietwaarde.
  const limitValueRequired = selectedLimitName?.trim().toLowerCase() === PERCENTAGE_LIMIT_NAME;

  function updateField<K extends keyof ProductInput>(field: K, value: ProductInput[K]) {
    setForm((current) => ({ ...current, [field]: value }));
  }

  async function handleSubmit() {
    setIsSubmitting(true);
    try {
      let savedProduct = isEditing ? await updateProduct(product.id, form) : await createProduct(form);
      // Then the picture: upload the picked file, or remove the old one.
      // The product's fields are already saved even if this step fails.
      try {
        if (image) {
          savedProduct = await uploadProductImage(savedProduct.id, image);
        } else if (removeImage && savedProduct.has_image) {
          savedProduct = await deleteProductImage(savedProduct.id);
        }
      } catch (imageError) {
        onSaved(savedProduct);
        const detail = imageError instanceof ApiError ? imageError.message : "";
        toast.error(t("imageUploadFailed", { detail }));
        return;
      }
      toast.success(isEditing ? t("productUpdated") : t("productCreated"));
      onSaved(savedProduct);
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
          <div className="col-span-2 flex flex-col gap-2">
            <Label htmlFor="product-name">
              {t("nameLabel")} <span aria-hidden="true" className="text-destructive">*</span>
            </Label>
            <Input id="product-name" value={form.name} onChange={(event) => updateField("name", event.target.value)} />
          </div>
          <div className="flex flex-col gap-2">
            <Label htmlFor="product-type">
              {t("typeLabel")} <span aria-hidden="true" className="text-destructive">*</span>
            </Label>
            <Select
              value={form.type_id ? String(form.type_id) : NO_SELECTION_VALUE}
              onValueChange={(value) => updateField("type_id", value && value !== NO_SELECTION_VALUE ? Number(value) : null)}
            >
              <SelectTrigger id="product-type">
                <SelectValue>
                  {(value: string | null) =>
                    productTypes.find((productType) => String(productType.id) === value)?.name ?? t("noSelection")
                  }
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
            <Label htmlFor="product-warehouse">
              {t("warehouseLabel")} <span aria-hidden="true" className="text-destructive">*</span>
            </Label>
            <Select
              value={form.warehouse_id ? String(form.warehouse_id) : NO_SELECTION_VALUE}
              onValueChange={(value) => updateField("warehouse_id", value && value !== NO_SELECTION_VALUE ? Number(value) : null)}
            >
              <SelectTrigger id="product-warehouse">
                <SelectValue>
                  {(value: string | null) =>
                    warehouses.find((warehouse) => String(warehouse.id) === value)?.name ?? t("noSelection")
                  }
                </SelectValue>
              </SelectTrigger>
              <SelectContent>
                {warehouses.map((warehouse) => (
                  <SelectItem key={warehouse.id} value={String(warehouse.id)}>
                    {warehouse.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="flex flex-col gap-2">
            <Label htmlFor="product-warehouse-location">{t("warehouseLocationLabel")}</Label>
            <Input
              id="product-warehouse-location"
              value={form.warehouse_location ?? ""}
              onChange={(event) => updateField("warehouse_location", event.target.value)}
            />
          </div>
          <div className="flex flex-col gap-2">
            <Label htmlFor="product-category">
              {t("categoryLabel")} <span aria-hidden="true" className="text-destructive">*</span>
            </Label>
            <Select
              value={form.category_id ? String(form.category_id) : NO_SELECTION_VALUE}
              onValueChange={(value) => updateField("category_id", value && value !== NO_SELECTION_VALUE ? Number(value) : null)}
            >
              <SelectTrigger id="product-category">
                <SelectValue>
                  {(value: string | null) =>
                    productCategories.find((productCategory) => String(productCategory.id) === value)?.name ??
                    t("noSelection")
                  }
                </SelectValue>
              </SelectTrigger>
              <SelectContent>
                {productCategories.map((productCategory) => (
                  <SelectItem key={productCategory.id} value={String(productCategory.id)}>
                    {productCategory.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          {/* The product's limits, grouped in one framed box. */}
          <fieldset className="col-span-2 rounded-md border bg-muted/30 p-3">
            <legend className="px-1 text-sm font-medium">{t("limitsLabel")}</legend>
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              <div className="flex flex-col gap-2">
                <Label htmlFor="product-limit">
                  {t("limitLabel")} <span aria-hidden="true" className="text-destructive">*</span>
                </Label>
                <Select
                  value={form.limit_id ? String(form.limit_id) : NO_SELECTION_VALUE}
                  onValueChange={(value) => updateField("limit_id", value && value !== NO_SELECTION_VALUE ? Number(value) : null)}
                >
                  <SelectTrigger id="product-limit" className="w-full">
                    <SelectValue>
                      {(value: string | null) =>
                        productLimits.find((productLimit) => String(productLimit.id) === value)?.name ?? t("noSelection")
                      }
                    </SelectValue>
                  </SelectTrigger>
                  <SelectContent>
                    {productLimits.map((productLimit) => (
                      <SelectItem key={productLimit.id} value={String(productLimit.id)}>
                        {productLimit.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="flex flex-col gap-2">
                {/* The value of the chosen Limiet: named after it, and only editable once one is chosen. */}
                <Label htmlFor="product-limit-value">
                  {selectedLimitName ? t("limitValueForLabel", { limit: selectedLimitName }) : t("limitValueLabel")}
                  {limitValueRequired && (
                    <>
                      {" "}
                      <span aria-hidden="true" className="text-destructive">*</span>
                    </>
                  )}
                </Label>
                <Input
                  id="product-limit-value"
                  type="number"
                  min={0}
                  step={1}
                  disabled={!form.limit_id}
                  value={form.limit_value ?? ""}
                  onChange={(event) =>
                    updateField(
                      "limit_value",
                      event.target.value === "" ? null : Math.max(0, Number.parseInt(event.target.value, 10) || 0),
                    )
                  }
                />
              </div>
              <div className="flex flex-col gap-2">
                {/* The most pieces a kar may hold before it's "Geleverd", with its explanation in a tooltip. */}
                <div className="flex items-center gap-1.5">
                  <Label htmlFor="product-max-initial-stock">{t("maxInitialStockLabel")}</Label>
                  <TooltipProvider delay={200}>
                    <Tooltip>
                      <TooltipTrigger
                        render={
                          <button
                            type="button"
                            aria-label={t("maxInitialStockHelp")}
                            className="cursor-help text-muted-foreground hover:text-foreground"
                          />
                        }
                      >
                        <Info className="size-4" />
                      </TooltipTrigger>
                      <TooltipContent className="max-w-xs text-sm">{t("maxInitialStockHelp")}</TooltipContent>
                    </Tooltip>
                  </TooltipProvider>
                </div>
                <Input
                  id="product-max-initial-stock"
                  type="number"
                  min={0}
                  step={1}
                  value={form.max_initial_stock ?? ""}
                  onChange={(event) =>
                    updateField(
                      "max_initial_stock",
                      event.target.value === "" ? null : Math.max(0, Number.parseInt(event.target.value, 10) || 0),
                    )
                  }
                />
              </div>
            </div>
          </fieldset>

          {/* The product's yes/no properties, grouped in one framed box. */}
          <fieldset className="col-span-2 rounded-md border bg-muted/30 p-3">
            <legend className="px-1 text-sm font-medium">{t("propertiesLabel")}</legend>
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              <div className="flex items-center gap-2">
                <Checkbox
                  id="product-consumable"
                  checked={form.is_consumable ?? false}
                  onCheckedChange={(checked) => updateField("is_consumable", checked === true)}
                />
                <Label htmlFor="product-consumable">{t("consumableLabel")}</Label>
              </div>
              <div className="flex items-center gap-2">
                <Checkbox
                  id="product-blocked"
                  checked={form.is_blocked ?? false}
                  onCheckedChange={(checked) => updateField("is_blocked", checked === true)}
                />
                <Label htmlFor="product-blocked">{t("blockedLabel")}</Label>
              </div>
              <div className="flex items-center gap-2">
                <Checkbox
                  id="product-logistics"
                  checked={form.is_logistics_product ?? false}
                  onCheckedChange={(checked) => updateField("is_logistics_product", checked === true)}
                />
                <Label htmlFor="product-logistics">{t("logisticsProductLabel")}</Label>
              </div>
              <div className="flex items-center gap-2">
                <Checkbox
                  id="product-tag-managed"
                  checked={form.is_tag_managed ?? false}
                  onCheckedChange={(checked) => updateField("is_tag_managed", checked === true)}
                />
                <Label htmlFor="product-tag-managed">{t("tagManagedLabel")}</Label>
              </div>
            </div>
          </fieldset>

          {/* StockMaster (module-4): where returned goods go, and the
              minimum stock of a consumable (reorder alert). */}
          <div className="flex flex-col gap-2">
            <Label htmlFor="product-stock-return">
              {t("stockReturnToLabel")} <span aria-hidden="true" className="text-destructive">*</span>
            </Label>
            <Select
              value={form.stock_return_to ?? "kar"}
              onValueChange={(value) => updateField("stock_return_to", value === "free" ? "free" : "kar")}
            >
              <SelectTrigger id="product-stock-return" className="w-full">
                <SelectValue>
                  {(value: string | null) => (value === "free" ? t("stockReturnFree") : t("stockReturnKar"))}
                </SelectValue>
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="kar">{t("stockReturnKar")}</SelectItem>
                <SelectItem value="free">{t("stockReturnFree")}</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div className="flex flex-col gap-2">
            <Label htmlFor="product-min-stock">{t("minStockLabel")}</Label>
            <Input
              id="product-min-stock"
              type="number"
              min={0}
              step={1}
              disabled={!form.is_consumable}
              placeholder={form.is_consumable ? "" : t("minStockConsumableOnly")}
              value={form.min_stock ?? ""}
              onChange={(event) =>
                updateField("min_stock", event.target.value === "" ? null : Math.max(0, Number.parseInt(event.target.value, 10) || 0))
              }
            />
          </div>

          <div className="col-span-2 flex flex-col gap-2">
            <Label htmlFor="product-description">{t("descriptionLabel")}</Label>
            <Textarea
              id="product-description"
              value={form.description ?? ""}
              onChange={(event) => updateField("description", event.target.value)}
            />
          </div>

          {/* The product's picture: preview, file button and "remove". */}
          <div className="col-span-2 flex flex-col gap-2">
            <Label htmlFor="product-image">{t("imageLabel")}</Label>
            {displayedImageUrl && (
              // A plain <img> is needed here: the source is a same-site backend
              // URL (or a local blob: preview), not a Next-optimizable asset.
              // eslint-disable-next-line @next/next/no-img-element
              <img
                src={displayedImageUrl}
                alt={t("imageLabel")}
                className="max-h-40 w-auto self-center rounded-md border object-contain"
              />
            )}
            <div className="flex items-center gap-2">
              <Input
                key={fileInputKey}
                id="product-image"
                type="file"
                accept={ACCEPTED_IMAGE_TYPES}
                onChange={(event) => handleImagePicked(event.target.files?.[0] ?? null)}
              />
              {displayedImageUrl && (
                <Button type="button" variant="outline" onClick={handleRemoveImage}>
                  <ImageOff className="size-4" />
                  {t("removeImage")}
                </Button>
              )}
            </div>
            <p className="text-xs text-muted-foreground">{t("imageHint")}</p>
          </div>

          {/* The cost of one piece, in euro — optional. */}
          <div className="col-span-2 flex flex-col gap-2">
            <Label htmlFor="product-cost">{t("costLabel")}</Label>
            <div className="relative">
              <span className="pointer-events-none absolute top-1/2 left-3 -translate-y-1/2 text-sm text-muted-foreground">
                €
              </span>
              <Input
                id="product-cost"
                type="number"
                min={0}
                step="0.01"
                inputMode="decimal"
                className="pl-7"
                value={form.cost ?? ""}
                onChange={(event) =>
                  updateField(
                    "cost",
                    // Rounded to cents, like the backend stores it.
                    event.target.value === ""
                      ? null
                      : Math.round(Math.max(0, Number(event.target.value) || 0) * 100) / 100,
                  )
                }
              />
            </div>
          </div>
        </div>

        <DialogFooter className="items-center">
          <p className="mr-auto text-xs text-muted-foreground">{t("requiredHint")}</p>
          <Button
            onClick={handleSubmit}
            disabled={
              isSubmitting ||
              !form.name ||
              !form.type_id ||
              !form.warehouse_id ||
              !form.category_id ||
              !form.limit_id ||
              (limitValueRequired && form.limit_value == null)
            }
          >
            {isEditing ? t("change") : t("newProduct")}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

interface DeleteProductAlertDialogProps {
  product: Product;
  onDeleted: (productId: number) => void;
}

function DeleteProductAlertDialog({ product, onDeleted }: DeleteProductAlertDialogProps) {
  const t = useTranslations("masterdata.products");
  const tCommon = useTranslations("common");
  const [isOpen, setIsOpen] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);

  async function handleConfirmDelete() {
    setIsDeleting(true);
    try {
      await deleteProduct(product.id);
      toast.success(t("productDeleted"));
      onDeleted(product.id);
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
          <AlertDialogDescription>{t("deleteConfirmDescription", { name: product.name })}</AlertDialogDescription>
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
