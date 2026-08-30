"use client";

// MasterData's "Products" screen: a table of products with add/change/
// delete, following the same dialog/table pattern as season-management.tsx
// — the create/edit dialog covers every field from the reference
// "Producten" screen except image upload, which is a later step.

import { useState } from "react";
import { Pencil, Trash2 } from "lucide-react";
import { useTranslations } from "next-intl";
import { toast } from "sonner";
import { useRouter } from "@/i18n/navigation";
import { ApiError, createProduct, deleteProduct, updateProduct } from "@/lib/api";
import type { Product, ProductInput } from "@/lib/types";
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
import { Textarea } from "@/components/ui/textarea";

interface ProductsManagementProps {
  initialProducts: Product[];
}

const EMPTY_FORM: ProductInput = {
  name: "",
  type: "",
  warehouse: "",
  warehouse_location: "",
  category: "",
  is_consumable: false,
  is_blocked: false,
  is_logistics_product: false,
  limit_mode: "",
  description: "",
};

function toFormValues(product: Product): ProductInput {
  return {
    name: product.name,
    type: product.type ?? "",
    warehouse: product.warehouse ?? "",
    warehouse_location: product.warehouse_location ?? "",
    category: product.category ?? "",
    is_consumable: product.is_consumable,
    is_blocked: product.is_blocked,
    is_logistics_product: product.is_logistics_product,
    limit_mode: product.limit_mode ?? "",
    description: product.description ?? "",
  };
}

export function ProductsManagement({ initialProducts }: ProductsManagementProps) {
  const t = useTranslations("masterdata.products");
  const router = useRouter();

  const [products, setProducts] = useState(initialProducts);

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
          <h1 className="text-2xl font-semibold tracking-tight">{t("title")}</h1>
          <p className="text-muted-foreground">{t("description")}</p>
        </div>
        <ProductFormDialog trigger={<Button>{t("newProduct")}</Button>} onSaved={upsert} />
      </div>

      <div className="overflow-x-auto rounded-md border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>{t("columnName")}</TableHead>
              <TableHead>{t("columnType")}</TableHead>
              <TableHead>{t("columnWarehouse")}</TableHead>
              <TableHead>{t("columnCategory")}</TableHead>
              <TableHead className="text-right">{t("tableActions")}</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {products.map((product) => (
              <TableRow key={product.id}>
                <TableCell className="font-medium">{product.name}</TableCell>
                <TableCell className="text-muted-foreground">{product.type}</TableCell>
                <TableCell className="text-muted-foreground">{product.warehouse}</TableCell>
                <TableCell className="text-muted-foreground">{product.category}</TableCell>
                <TableCell>
                  <div className="flex justify-end gap-1">
                    <ProductFormDialog
                      product={product}
                      trigger={
                        <Button variant="ghost" size="icon" aria-label={t("change")} title={t("change")}>
                          <Pencil className="size-4" />
                        </Button>
                      }
                      onSaved={upsert}
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
  trigger: React.ReactElement;
  onSaved: (product: Product) => void;
}

function ProductFormDialog({ product, trigger, onSaved }: ProductFormDialogProps) {
  const t = useTranslations("masterdata.products");
  const isEditing = product !== undefined;
  const [isOpen, setIsOpen] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [form, setForm] = useState<ProductInput>(product ? toFormValues(product) : EMPTY_FORM);

  function handleOpenChange(open: boolean) {
    setIsOpen(open);
    if (open) {
      // Start from the product's latest known values each time the
      // dialog is opened, in case they changed since last time.
      setForm(product ? toFormValues(product) : EMPTY_FORM);
    }
  }

  function updateField<K extends keyof ProductInput>(field: K, value: ProductInput[K]) {
    setForm((current) => ({ ...current, [field]: value }));
  }

  async function handleSubmit() {
    setIsSubmitting(true);
    try {
      const savedProduct = isEditing ? await updateProduct(product.id, form) : await createProduct(form);
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
            <Label htmlFor="product-name">{t("nameLabel")}</Label>
            <Input id="product-name" value={form.name} onChange={(event) => updateField("name", event.target.value)} />
          </div>
          <div className="flex flex-col gap-2">
            <Label htmlFor="product-type">{t("typeLabel")}</Label>
            <Input id="product-type" value={form.type ?? ""} onChange={(event) => updateField("type", event.target.value)} />
          </div>
          <div className="flex flex-col gap-2">
            <Label htmlFor="product-warehouse">{t("warehouseLabel")}</Label>
            <Input
              id="product-warehouse"
              value={form.warehouse ?? ""}
              onChange={(event) => updateField("warehouse", event.target.value)}
            />
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
            <Label htmlFor="product-category">{t("categoryLabel")}</Label>
            <Input
              id="product-category"
              value={form.category ?? ""}
              onChange={(event) => updateField("category", event.target.value)}
            />
          </div>
          <div className="flex flex-col gap-2">
            <Label htmlFor="product-limit">{t("limitLabel")}</Label>
            <Input
              id="product-limit"
              value={form.limit_mode ?? ""}
              onChange={(event) => updateField("limit_mode", event.target.value)}
            />
          </div>

          <div className="col-span-2 flex flex-col gap-3 pt-2">
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
          </div>

          <div className="col-span-2 flex flex-col gap-2">
            <Label htmlFor="product-description">{t("descriptionLabel")}</Label>
            <Textarea
              id="product-description"
              value={form.description ?? ""}
              onChange={(event) => updateField("description", event.target.value)}
            />
          </div>
        </div>

        <DialogFooter>
          <Button onClick={handleSubmit} disabled={isSubmitting || !form.name}>
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
