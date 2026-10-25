"use client";

// Atelier's "Masterdata > Artikelen" screen: the clothing catalogue. Each
// article has a unique code, a name, optional colour/description/price, a
// picture, and the sizes it comes in — ticked in a checklist grouped by fit
// (Dames, Heren, Unisex), each with an optional minimum stock and its share
// (%) of the standard size split used to estimate what to prepare. Follows the
// same table + dialog pattern as StockMaster's products-management.tsx: the
// picture is uploaded right after the fields are saved.

import { useEffect, useMemo, useState } from "react";
import { Pencil, Shirt, Trash2 } from "lucide-react";
import { useTranslations } from "next-intl";
import { toast } from "sonner";
import { useRouter } from "@/i18n/navigation";
import {
  ApiError,
  atelierArticleImageUrl,
  createAtelierArticle,
  deleteAtelierArticle,
  deleteAtelierArticleImage,
  updateAtelierArticle,
  uploadAtelierArticleImage,
} from "@/lib/api";
import type { AtelierArticle, AtelierArticleInput, AtelierFit, AtelierSize } from "@/lib/types";
import { cn } from "@/lib/utils";
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
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Textarea } from "@/components/ui/textarea";
import { ATELIER_FITS, sizeLabel, sortSizes } from "@/components/module-5/atelier-sizes";

// The picture types the backend accepts (it also refuses anything over 5 MB).
const ACCEPTED_IMAGE_TYPES = "image/png,image/jpeg,image/webp";
const MAX_IMAGE_BYTES = 5 * 1024 * 1024;

const EMPTY_FORM: AtelierArticleInput = {
  code: "",
  name: "",
  description: null,
  colour: null,
  cost: null,
  is_tag_managed: false,
  active: true,
  sizes: [],
};

function toFormValues(article: AtelierArticle): AtelierArticleInput {
  return {
    code: article.code,
    name: article.name,
    description: article.description,
    colour: article.colour,
    cost: article.cost,
    is_tag_managed: article.is_tag_managed,
    active: article.active,
    sizes: article.sizes.map(({ size_id, min_stock, size_share_pct, active }) => ({
      size_id,
      min_stock,
      size_share_pct,
      active,
    })),
  };
}

interface ArticleManagementProps {
  initialArticles: AtelierArticle[];
  sizes: AtelierSize[];
  canCreate: boolean;
  canEdit: boolean;
  canDelete: boolean;
}

export function ArticleManagement({ initialArticles, sizes, canCreate, canEdit, canDelete }: ArticleManagementProps) {
  const t = useTranslations("atelier.articles");
  const tFit = useTranslations("atelier.fits");
  const router = useRouter();

  const [articles, setArticles] = useState(initialArticles);
  const sortedSizes = useMemo(() => sortSizes(sizes), [sizes]);
  const sizesById = useMemo(() => new Map(sizes.map((size) => [size.id, size])), [sizes]);

  function upsert(saved: AtelierArticle) {
    setArticles((current) =>
      [...current.filter((article) => article.id !== saved.id), saved].sort((a, b) => a.name.localeCompare(b.name)),
    );
    router.refresh();
  }

  // The article's sizes as one short text, e.g. "S · Heren, M · Heren".
  function sizesText(article: AtelierArticle) {
    return article.sizes
      .map((row) => sizesById.get(row.size_id))
      .filter((size): size is AtelierSize => size !== undefined)
      .map((size) => sizeLabel(size, (fit) => tFit(fit)))
      .join(", ");
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight underline">{t("title")}</h1>
          <p className="text-muted-foreground">{t("description")}</p>
        </div>
        {canCreate && (
          <ArticleFormDialog trigger={<Button>{t("newArticle")}</Button>} sizes={sortedSizes} onSaved={upsert} />
        )}
      </div>

      <div className="rounded-md border [&>div]:max-h-[65vh] [&>div]:overflow-y-auto">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="sticky top-0 z-20 w-16 bg-background text-center font-bold underline">
                {t("columnImage")}
              </TableHead>
              <TableHead className="sticky top-0 z-20 bg-background font-bold underline">{t("columnCode")}</TableHead>
              <TableHead className="sticky top-0 z-20 bg-background font-bold underline">{t("columnName")}</TableHead>
              <TableHead className="sticky top-0 z-20 bg-background font-bold underline">{t("columnColour")}</TableHead>
              <TableHead className="sticky top-0 z-20 bg-background font-bold underline">{t("columnSizes")}</TableHead>
              <TableHead className="sticky top-0 z-20 bg-background font-bold underline">{t("columnActive")}</TableHead>
              <TableHead className="sticky top-0 right-0 z-30 bg-background text-right font-bold underline">
                {t("tableActions")}
              </TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {articles.length === 0 && (
              <TableRow>
                <TableCell colSpan={7} className="text-center text-muted-foreground">
                  {t("empty")}
                </TableCell>
              </TableRow>
            )}
            {articles.map((article) => (
              <TableRow key={article.id} className="group">
                <TableCell>
                  <ArticleThumb article={article} />
                </TableCell>
                <TableCell className="font-mono text-sm">{article.code}</TableCell>
                <TableCell className="font-medium">{article.name}</TableCell>
                <TableCell className="text-muted-foreground">{article.colour}</TableCell>
                <TableCell className="max-w-xs text-sm whitespace-normal text-muted-foreground">
                  {sizesText(article)}
                </TableCell>
                <TableCell>
                  {article.active ? t("activeYes") : <Badge variant="secondary">{t("activeNo")}</Badge>}
                </TableCell>
                <TableCell className="sticky right-0 z-10 bg-background group-hover:bg-muted/50">
                  <div className="flex justify-end gap-1">
                    {canEdit && (
                      <ArticleFormDialog
                        article={article}
                        sizes={sortedSizes}
                        trigger={
                          <Button variant="ghost" size="icon" aria-label={t("change")} title={t("change")}>
                            <Pencil className="size-4" />
                          </Button>
                        }
                        onSaved={upsert}
                      />
                    )}
                    {canDelete && (
                      <DeleteArticleDialog
                        article={article}
                        onDeleted={(articleId) => {
                          setArticles((current) => current.filter((item) => item.id !== articleId));
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

/** An article's small picture, or a shirt icon in the same square. */
export function ArticleThumb({ article }: { article: Pick<AtelierArticle, "id" | "name" | "has_image" | "image_updated_at"> }) {
  return (
    <div className="mx-auto flex size-10 shrink-0 items-center justify-center overflow-hidden rounded-md border bg-muted/40">
      {article.has_image ? (
        // eslint-disable-next-line @next/next/no-img-element -- authenticated API image, not a static asset
        <img
          src={atelierArticleImageUrl(article.id, article.image_updated_at)}
          alt={article.name}
          loading="lazy"
          className="size-full object-contain"
        />
      ) : (
        <Shirt className="size-4 text-muted-foreground" />
      )}
    </div>
  );
}

interface ArticleFormDialogProps {
  article?: AtelierArticle;
  /** Every size, already sorted by fit and order. */
  sizes: AtelierSize[];
  trigger: React.ReactElement;
  onSaved: (article: AtelierArticle) => void;
}

function ArticleFormDialog({ article, sizes, trigger, onSaved }: ArticleFormDialogProps) {
  const t = useTranslations("atelier.articles");
  const tFit = useTranslations("atelier.fits");
  const isEditing = article !== undefined;
  const [isOpen, setIsOpen] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [form, setForm] = useState<AtelierArticleInput>(EMPTY_FORM);
  // The price as typed (so "7," can be typed on the way to "7,50").
  const [costText, setCostText] = useState("");
  // The picture picked with the file button (uploaded on "save"), and
  // whether the current picture should be removed on save.
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

  // The sizes offered: every active one, plus inactive ones the article already has.
  const offeredSizes = sizes.filter(
    (size) => size.active || article?.sizes.some((row) => row.size_id === size.id),
  );
  const ticked = new Map(form.sizes.map((row) => [row.size_id, row]));

  const displayedImageUrl =
    previewUrl ??
    (article?.has_image && !removeImage ? atelierArticleImageUrl(article.id, article.image_updated_at) : null);

  function pickImage(file: File | null) {
    setImage(file);
    setPreviewUrl(file ? URL.createObjectURL(file) : null);
  }

  function handleOpenChange(open: boolean) {
    setIsOpen(open);
    if (open) {
      // Start from the article's latest values every time the dialog opens.
      const values = article ? toFormValues(article) : EMPTY_FORM;
      setForm(values);
      setCostText(values.cost !== null ? String(values.cost).replace(".", ",") : "");
      pickImage(null);
      setRemoveImage(false);
      setFileInputKey((key) => key + 1);
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

  function updateField<K extends keyof AtelierArticleInput>(field: K, value: AtelierArticleInput[K]) {
    setForm((current) => ({ ...current, [field]: value }));
  }

  // Tick or untick one size; a newly ticked size starts active, without a minimum.
  function toggleSize(sizeId: number, checked: boolean) {
    setForm((current) => ({
      ...current,
      sizes: checked
        ? [...current.sizes, { size_id: sizeId, min_stock: null, size_share_pct: null, active: true }]
        : current.sizes.filter((row) => row.size_id !== sizeId),
    }));
  }

  function setMinStock(sizeId: number, value: string) {
    const minStock = value === "" ? null : Math.max(0, Number.parseInt(value, 10) || 0);
    setForm((current) => ({
      ...current,
      sizes: current.sizes.map((row) => (row.size_id === sizeId ? { ...row, min_stock: minStock } : row)),
    }));
  }

  function setShare(sizeId: number, value: string) {
    const share = value === "" ? null : Math.min(100, Math.max(0, Number(value.replace(",", ".")) || 0));
    setForm((current) => ({
      ...current,
      sizes: current.sizes.map((row) => (row.size_id === sizeId ? { ...row, size_share_pct: share } : row)),
    }));
  }

  // The size split is all-or-nothing: once a share is filled in, the total must be 100%.
  const shareTotal = form.sizes.reduce((sum, row) => sum + (row.size_share_pct ?? 0), 0);
  const splitUsed = form.sizes.some((row) => row.size_share_pct !== null);
  const splitInvalid = splitUsed && Math.abs(shareTotal - 100) > 0.001;

  // The typed price as a number (comma or dot), null when empty, NaN when invalid.
  const cost = costText.trim() === "" ? null : Number(costText.trim().replace(",", "."));
  const costInvalid = cost !== null && (Number.isNaN(cost) || cost < 0);

  async function handleSubmit() {
    setIsSubmitting(true);
    try {
      const payload: AtelierArticleInput = {
        ...form,
        code: form.code.trim(),
        name: form.name.trim(),
        description: form.description?.trim() || null,
        colour: form.colour?.trim() || null,
        cost: cost === null ? null : Math.round(cost * 100) / 100,
      };
      let saved = isEditing ? await updateAtelierArticle(article.id, payload) : await createAtelierArticle(payload);
      // Then the picture: upload the picked file, or remove the old one.
      // The fields are already saved even if this step fails.
      try {
        if (image) {
          saved = await uploadAtelierArticleImage(saved.id, image);
        } else if (removeImage && saved.has_image) {
          saved = await deleteAtelierArticleImage(saved.id);
        }
      } catch (imageError) {
        onSaved(saved);
        toast.error(t("imageUploadFailed", { detail: imageError instanceof ApiError ? imageError.message : "" }));
        return;
      }
      toast.success(isEditing ? t("articleUpdated") : t("articleCreated"));
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
      <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-2xl">
        <DialogHeader>
          <DialogTitle>{isEditing ? t("changeTitle") : t("createTitle")}</DialogTitle>
          <DialogDescription>{t("formDescription")}</DialogDescription>
        </DialogHeader>

        <div className="grid grid-cols-2 gap-4">
          <div className="flex flex-col gap-2">
            <Label htmlFor="atelier-article-code">
              {t("codeLabel")} <span aria-hidden="true" className="text-destructive">*</span>
            </Label>
            <Input
              id="atelier-article-code"
              value={form.code}
              placeholder="TS-CREW-ZW"
              onChange={(event) => updateField("code", event.target.value)}
            />
          </div>
          <div className="flex flex-col gap-2">
            <Label htmlFor="atelier-article-name">
              {t("nameLabel")} <span aria-hidden="true" className="text-destructive">*</span>
            </Label>
            <Input id="atelier-article-name" value={form.name} onChange={(event) => updateField("name", event.target.value)} />
          </div>
          <div className="flex flex-col gap-2">
            <Label htmlFor="atelier-article-colour">{t("colourLabel")}</Label>
            <Input
              id="atelier-article-colour"
              value={form.colour ?? ""}
              onChange={(event) => updateField("colour", event.target.value)}
            />
          </div>
          <div className="flex flex-col gap-2">
            <Label htmlFor="atelier-article-cost">{t("costLabel")}</Label>
            <Input
              id="atelier-article-cost"
              inputMode="decimal"
              value={costText}
              aria-invalid={costInvalid}
              onChange={(event) => setCostText(event.target.value)}
            />
          </div>
          <div className="col-span-2 flex flex-col gap-2">
            <Label htmlFor="atelier-article-description">{t("descriptionLabel")}</Label>
            <Textarea
              id="atelier-article-description"
              rows={2}
              value={form.description ?? ""}
              onChange={(event) => updateField("description", event.target.value)}
            />
          </div>

          {/* The sizes the article comes in, per fit, each with its minimum stock. */}
          <fieldset className="col-span-2 rounded-md border bg-muted/30 p-3">
            <legend className="px-1 text-sm font-medium">{t("sizesLabel")}</legend>
            {offeredSizes.length === 0 && <p className="text-sm text-muted-foreground">{t("noSizes")}</p>}
            <p className="mb-2 text-xs text-muted-foreground">{t("sizesHelp")}</p>
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
              {ATELIER_FITS.map((fit: AtelierFit) => {
                const fitSizes = offeredSizes.filter((size) => size.fit === fit);
                if (fitSizes.length === 0) return null;
                return (
                  <div key={fit} className="flex flex-col gap-2">
                    <p className="text-sm font-semibold">{tFit(fit)}</p>
                    {fitSizes.map((size) => {
                      const row = ticked.get(size.id);
                      return (
                        <div key={size.id} className="flex items-center gap-2">
                          <Checkbox
                            id={`atelier-article-size-${size.id}`}
                            checked={row !== undefined}
                            onCheckedChange={(checked) => toggleSize(size.id, checked === true)}
                          />
                          <Label htmlFor={`atelier-article-size-${size.id}`} className="w-16">
                            {size.name}
                          </Label>
                          {row && (
                            <>
                              <Input
                                type="number"
                                min={0}
                                step={1}
                                className="h-7 w-16"
                                aria-label={t("minStockFor", { size: sizeLabel(size, (f) => tFit(f)) })}
                                placeholder={t("minStockPlaceholder")}
                                value={row.min_stock ?? ""}
                                onChange={(event) => setMinStock(size.id, event.target.value)}
                              />
                              <Input
                                type="number"
                                min={0}
                                max={100}
                                step={1}
                                className="h-7 w-16"
                                aria-label={t("shareFor", { size: sizeLabel(size, (f) => tFit(f)) })}
                                placeholder="%"
                                value={row.size_share_pct ?? ""}
                                onChange={(event) => setShare(size.id, event.target.value)}
                              />
                            </>
                          )}
                        </div>
                      );
                    })}
                  </div>
                );
              })}
            </div>
            {splitUsed && (
              <p className={cn("mt-2 text-sm", splitInvalid ? "text-destructive" : "text-muted-foreground")}>
                {t("shareTotal", { total: Math.round(shareTotal * 100) / 100 })}
              </p>
            )}
          </fieldset>

          {/* The picture: preview, pick a file, or remove it. */}
          <div className="col-span-2 flex items-center gap-4">
            <div className="flex size-20 shrink-0 items-center justify-center overflow-hidden rounded-md border bg-muted/40">
              {displayedImageUrl ? (
                // eslint-disable-next-line @next/next/no-img-element -- local preview or authenticated API image
                <img src={displayedImageUrl} alt={form.name} className="size-full object-contain" />
              ) : (
                <Shirt className="size-6 text-muted-foreground" />
              )}
            </div>
            <div className="flex flex-col gap-2">
              <Label htmlFor="atelier-article-image">{t("imageLabel")}</Label>
              <div className="flex items-center gap-2">
                <Input
                  key={fileInputKey}
                  id="atelier-article-image"
                  type="file"
                  accept={ACCEPTED_IMAGE_TYPES}
                  onChange={(event) => handleImagePicked(event.target.files?.[0] ?? null)}
                />
                {displayedImageUrl && (
                  <Button
                    type="button"
                    variant="outline"
                    onClick={() => {
                      pickImage(null);
                      setRemoveImage(true);
                      setFileInputKey((key) => key + 1);
                    }}
                  >
                    {t("removeImage")}
                  </Button>
                )}
              </div>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <Checkbox
              id="atelier-article-active"
              checked={form.active}
              onCheckedChange={(checked) => updateField("active", checked === true)}
            />
            <Label htmlFor="atelier-article-active">{t("activeLabel")}</Label>
          </div>
          <div className="flex items-center gap-2">
            <Checkbox
              id="atelier-article-tag-managed"
              checked={form.is_tag_managed}
              onCheckedChange={(checked) => updateField("is_tag_managed", checked === true)}
            />
            <Label htmlFor="atelier-article-tag-managed">{t("tagManagedLabel")}</Label>
          </div>
        </div>

        <DialogFooter>
          <Button
            onClick={handleSubmit}
            disabled={isSubmitting || !form.code.trim() || !form.name.trim() || costInvalid || splitInvalid}
          >
            {t("save")}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

interface DeleteArticleDialogProps {
  article: AtelierArticle;
  onDeleted: (articleId: number) => void;
}

function DeleteArticleDialog({ article, onDeleted }: DeleteArticleDialogProps) {
  const t = useTranslations("atelier.articles");
  const tCommon = useTranslations("common");
  const [isOpen, setIsOpen] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);

  async function handleConfirmDelete() {
    setIsDeleting(true);
    try {
      await deleteAtelierArticle(article.id);
      toast.success(t("articleDeleted"));
      onDeleted(article.id);
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
          <AlertDialogDescription>{t("deleteConfirmDescription", { name: article.name })}</AlertDialogDescription>
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
