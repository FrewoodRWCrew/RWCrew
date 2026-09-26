"use client";

// KarTracker's "Grondplan" screen: the list of ground plans of the event
// site (e.g. one per zone), each with its own image and south-west/
// north-east corner coordinates, so Kar Map can overlay them all in the
// right place — see kar-map.tsx/kar-map-leaflet.tsx for where those
// coordinates end up being used (one Leaflet ImageOverlay per plan).
// A table with add/change/delete, same shape as DistributiepuntManagement.

import { useEffect, useMemo, useState } from "react";
import { Pencil, Trash2 } from "lucide-react";
import { useTranslations } from "next-intl";
import { toast } from "sonner";
import { useRouter } from "@/i18n/navigation";
import {
  ApiError,
  createKarTrackerGroundplan,
  deleteKarTrackerGroundplan,
  karTrackerGroundplanImageUrl,
  updateKarTrackerGroundplan,
} from "@/lib/api";
import type { KarTrackerGroundplan } from "@/lib/types";
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

interface GroundplanManagementProps {
  initialGroundplans: KarTrackerGroundplan[];
  canCreate: boolean;
  canEdit: boolean;
}

// The form keeps every field as the raw input string, so a half-typed
// coordinate (e.g. "-" or "50.") isn't mangled while the user types.
interface GroundplanFormValues {
  name: string;
  swLatitude: string;
  swLongitude: string;
  neLatitude: string;
  neLongitude: string;
}

const EMPTY_FORM: GroundplanFormValues = { name: "", swLatitude: "", swLongitude: "", neLatitude: "", neLongitude: "" };

function toFormValues(groundplan: KarTrackerGroundplan): GroundplanFormValues {
  return {
    name: groundplan.name,
    swLatitude: groundplan.sw_latitude.toString(),
    swLongitude: groundplan.sw_longitude.toString(),
    neLatitude: groundplan.ne_latitude.toString(),
    neLongitude: groundplan.ne_longitude.toString(),
  };
}

function sortByName(groundplans: KarTrackerGroundplan[]) {
  return [...groundplans].sort((a, b) => a.name.localeCompare(b.name) || a.id - b.id);
}

export function GroundplanManagement({ initialGroundplans, canCreate, canEdit }: GroundplanManagementProps) {
  const t = useTranslations("karTracker.groundplan");
  const router = useRouter();
  const [groundplans, setGroundplans] = useState(initialGroundplans);

  // Insert a newly-created plan or replace an edited one, keeping the list
  // sorted by name the same way the backend returns it.
  function upsert(saved: KarTrackerGroundplan) {
    setGroundplans((current) => sortByName([...current.filter((item) => item.id !== saved.id), saved]));
    router.refresh();
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight underline">{t("title")}</h1>
          <p className="text-muted-foreground">{t("description")}</p>
        </div>
        {canCreate && <GroundplanFormDialog trigger={<Button>{t("newGroundplan")}</Button>} onSaved={upsert} />}
      </div>

      <div className="rounded-md border [&>div]:max-h-[65vh] [&>div]:overflow-y-auto">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="sticky top-0 z-20 bg-background font-bold underline">{t("columnImage")}</TableHead>
              <TableHead className="sticky top-0 z-20 bg-background font-bold underline">{t("columnName")}</TableHead>
              <TableHead className="sticky top-0 z-20 bg-background font-bold underline">{t("columnSouthWest")}</TableHead>
              <TableHead className="sticky top-0 z-20 bg-background font-bold underline">{t("columnNorthEast")}</TableHead>
              <TableHead className="sticky top-0 right-0 z-30 bg-background text-right font-bold underline">
                {t("tableActions")}
              </TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {groundplans.length === 0 && (
              <TableRow>
                <TableCell colSpan={5} className="text-center text-muted-foreground">
                  {t("empty")}
                </TableCell>
              </TableRow>
            )}
            {groundplans.map((groundplan) => (
              <TableRow key={groundplan.id} className="group">
                <TableCell>
                  {/* A plain <img> is needed here: the source is a same-site
                      backend URL, not a Next-optimizable asset. */}
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img
                    src={karTrackerGroundplanImageUrl(groundplan.id, groundplan.updated_at)}
                    alt={groundplan.name}
                    className="h-12 w-20 rounded border object-contain"
                  />
                </TableCell>
                <TableCell className="font-medium">{groundplan.name}</TableCell>
                <TableCell className="text-muted-foreground">
                  {groundplan.sw_latitude}, {groundplan.sw_longitude}
                </TableCell>
                <TableCell className="text-muted-foreground">
                  {groundplan.ne_latitude}, {groundplan.ne_longitude}
                </TableCell>
                <TableCell className="sticky right-0 z-10 bg-background group-hover:bg-muted/50">
                  <div className="flex justify-end gap-1">
                    {canEdit && (
                      <GroundplanFormDialog
                        groundplan={groundplan}
                        trigger={
                          <Button variant="ghost" size="icon" aria-label={t("change")} title={t("change")}>
                            <Pencil className="size-4" />
                          </Button>
                        }
                        onSaved={upsert}
                      />
                    )}
                    <DeleteGroundplanAlertDialog
                      groundplan={groundplan}
                      onDeleted={(id) => {
                        setGroundplans((current) => current.filter((item) => item.id !== id));
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

interface GroundplanFormDialogProps {
  groundplan?: KarTrackerGroundplan;
  trigger: React.ReactElement;
  onSaved: (groundplan: KarTrackerGroundplan) => void;
}

function GroundplanFormDialog({ groundplan, trigger, onSaved }: GroundplanFormDialogProps) {
  const t = useTranslations("karTracker.groundplan");
  const isEditing = groundplan !== undefined;
  const [isOpen, setIsOpen] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [form, setForm] = useState<GroundplanFormValues>(groundplan ? toFormValues(groundplan) : EMPTY_FORM);
  const [image, setImage] = useState<File | null>(null);

  // A newly-picked file gets previewed via a local object URL, created
  // during render (not in an effect, so there's no setState-in-effect
  // cascade) — the effect below only handles revoking it, whenever it's
  // replaced or the component unmounts, so it doesn't leak.
  const previewUrl = useMemo(() => (image ? URL.createObjectURL(image) : null), [image]);
  useEffect(() => {
    return () => {
      if (previewUrl) URL.revokeObjectURL(previewUrl);
    };
  }, [previewUrl]);

  // When editing without picking a new file, show the plan's current image.
  const displayedImageUrl =
    previewUrl ?? (groundplan ? karTrackerGroundplanImageUrl(groundplan.id, groundplan.updated_at) : null);

  const coordinates = [form.swLatitude, form.swLongitude, form.neLatitude, form.neLongitude];
  const hasValidCoordinates = coordinates.every((value) => value.trim() !== "" && !Number.isNaN(Number(value)));
  // A new plan needs an image; an existing one keeps its old image unless a new one is picked.
  const canSubmit = form.name.trim() !== "" && hasValidCoordinates && (isEditing || image !== null);

  function handleOpenChange(open: boolean) {
    setIsOpen(open);
    if (open) {
      // Start from the plan's latest known values each time the dialog is
      // opened, and forget any file picked the previous time.
      setForm(groundplan ? toFormValues(groundplan) : EMPTY_FORM);
      setImage(null);
    }
  }

  function updateField(field: keyof GroundplanFormValues, value: string) {
    setForm((current) => ({ ...current, [field]: value }));
  }

  async function handleSubmit() {
    setIsSubmitting(true);
    try {
      const formData = new FormData();
      formData.append("name", form.name.trim());
      formData.append("sw_latitude", form.swLatitude);
      formData.append("sw_longitude", form.swLongitude);
      formData.append("ne_latitude", form.neLatitude);
      formData.append("ne_longitude", form.neLongitude);
      if (image) formData.append("image", image);

      const saved = isEditing
        ? await updateKarTrackerGroundplan(groundplan.id, formData)
        : await createKarTrackerGroundplan(formData);
      toast.success(t("saveSuccess"));
      onSaved(saved);
      setIsOpen(false);
    } catch (error) {
      toast.error(error instanceof ApiError ? error.message : t("saveError"));
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
          <DialogDescription>{t("boundsDescription")}</DialogDescription>
        </DialogHeader>

        <div className="grid grid-cols-2 gap-4">
          <div className="col-span-2 flex flex-col gap-2">
            <Label htmlFor="groundplan-name">{t("nameLabel")}</Label>
            <Input id="groundplan-name" value={form.name} maxLength={100} onChange={(event) => updateField("name", event.target.value)} />
          </div>

          <div className="col-span-2 flex flex-col gap-2">
            <Label htmlFor="groundplan-image">{isEditing ? t("chooseNewImage") : t("chooseImage")}</Label>
            {displayedImageUrl && (
              // A plain <img> is needed here: the source is a same-site backend
              // URL (or a local blob: preview), not a Next-optimizable asset.
              // eslint-disable-next-line @next/next/no-img-element
              <img src={displayedImageUrl} alt={t("imageLabel")} className="max-h-48 w-auto self-start rounded-md border object-contain" />
            )}
            <Input
              id="groundplan-image"
              type="file"
              accept="image/png,image/jpeg"
              onChange={(event) => setImage(event.target.files?.[0] ?? null)}
            />
          </div>

          <div className="flex flex-col gap-2">
            <Label htmlFor="groundplan-sw-lat">{t("swLatitude")}</Label>
            <Input id="groundplan-sw-lat" type="number" step="any" value={form.swLatitude} onChange={(event) => updateField("swLatitude", event.target.value)} />
          </div>
          <div className="flex flex-col gap-2">
            <Label htmlFor="groundplan-sw-lng">{t("swLongitude")}</Label>
            <Input id="groundplan-sw-lng" type="number" step="any" value={form.swLongitude} onChange={(event) => updateField("swLongitude", event.target.value)} />
          </div>
          <div className="flex flex-col gap-2">
            <Label htmlFor="groundplan-ne-lat">{t("neLatitude")}</Label>
            <Input id="groundplan-ne-lat" type="number" step="any" value={form.neLatitude} onChange={(event) => updateField("neLatitude", event.target.value)} />
          </div>
          <div className="flex flex-col gap-2">
            <Label htmlFor="groundplan-ne-lng">{t("neLongitude")}</Label>
            <Input id="groundplan-ne-lng" type="number" step="any" value={form.neLongitude} onChange={(event) => updateField("neLongitude", event.target.value)} />
          </div>
        </div>

        <DialogFooter>
          <Button onClick={handleSubmit} disabled={isSubmitting || !canSubmit}>
            {t("save")}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

interface DeleteGroundplanAlertDialogProps {
  groundplan: KarTrackerGroundplan;
  onDeleted: (groundplanId: number) => void;
}

function DeleteGroundplanAlertDialog({ groundplan, onDeleted }: DeleteGroundplanAlertDialogProps) {
  const t = useTranslations("karTracker.groundplan");
  const tCommon = useTranslations("common");
  const [isOpen, setIsOpen] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);

  async function handleConfirmDelete() {
    setIsDeleting(true);
    try {
      await deleteKarTrackerGroundplan(groundplan.id);
      toast.success(t("deleteSuccess"));
      onDeleted(groundplan.id);
      setIsOpen(false);
    } catch (error) {
      toast.error(error instanceof ApiError ? error.message : t("deleteError"));
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
          <AlertDialogDescription>{t("deleteConfirmDescription", { name: groundplan.name })}</AlertDialogDescription>
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
