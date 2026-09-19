"use client";

// KarTracker's "Grondplan" screen: upload the event site's ground-plan
// image and set its south-west/north-east corner coordinates, so Kar Map
// can overlay it in the right place — see kar-map.tsx/kar-map-leaflet.tsx
// for where those coordinates end up being used (a Leaflet ImageOverlay).
// Single-record settings form, same shape as TagScan's own Settings screen
// (components/module-1/tagscan-settings.tsx) — no table, no list.

import { useEffect, useMemo, useState } from "react";
import { useTranslations } from "next-intl";
import { toast } from "sonner";
import { ApiError, karTrackerGroundplanImageUrl, updateKarTrackerGroundplan } from "@/lib/api";
import type { KarTrackerGroundplan } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

interface GroundplanSettingsProps {
  initialData: KarTrackerGroundplan;
}

export function GroundplanSettings({ initialData }: GroundplanSettingsProps) {
  const t = useTranslations("karTracker.groundplan");
  const [groundplan, setGroundplan] = useState(initialData);
  const [image, setImage] = useState<File | null>(null);
  // Bumped after every successful save so the <img> tag's URL changes and
  // the browser re-fetches the (possibly just-replaced) image instead of
  // showing a stale cached copy — the endpoint's URL is otherwise static.
  const [cacheBust, setCacheBust] = useState(0);
  const [swLatitude, setSwLatitude] = useState(initialData.sw_latitude?.toString() ?? "");
  const [swLongitude, setSwLongitude] = useState(initialData.sw_longitude?.toString() ?? "");
  const [neLatitude, setNeLatitude] = useState(initialData.ne_latitude?.toString() ?? "");
  const [neLongitude, setNeLongitude] = useState(initialData.ne_longitude?.toString() ?? "");
  const [isSaving, setIsSaving] = useState(false);

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

  const coordinates = [swLatitude, swLongitude, neLatitude, neLongitude];
  const hasValidCoordinates = coordinates.every((value) => value.trim() !== "" && !Number.isNaN(Number(value)));

  function handleFileChange(event: React.ChangeEvent<HTMLInputElement>) {
    setImage(event.target.files?.[0] ?? null);
  }

  async function handleSave() {
    setIsSaving(true);
    try {
      const formData = new FormData();
      formData.append("sw_latitude", swLatitude);
      formData.append("sw_longitude", swLongitude);
      formData.append("ne_latitude", neLatitude);
      formData.append("ne_longitude", neLongitude);
      if (image) formData.append("image", image);

      const updated = await updateKarTrackerGroundplan(formData);
      setGroundplan(updated);
      setImage(null);
      setCacheBust((value) => value + 1);
      toast.success(t("saveSuccess"));
    } catch (error) {
      toast.error(error instanceof ApiError ? error.message : t("saveError"));
    } finally {
      setIsSaving(false);
    }
  }

  const currentImageUrl = groundplan.has_image ? `${karTrackerGroundplanImageUrl()}?v=${cacheBust}` : null;
  const displayedImageUrl = previewUrl ?? currentImageUrl;

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight underline">{t("title")}</h1>
        <p className="text-muted-foreground">{t("description")}</p>
      </div>

      <div className="flex max-w-2xl flex-col gap-4 rounded-md border p-4">
        <Label className="text-base font-bold underline">{t("imageLabel")}</Label>
        {displayedImageUrl ? (
          // A plain <img> is needed here: the source is a same-site backend
          // URL (or a local blob: preview), not a Next-optimizable asset.
          // eslint-disable-next-line @next/next/no-img-element
          <img src={displayedImageUrl} alt={t("imageLabel")} className="max-h-64 w-auto rounded-md border object-contain" />
        ) : (
          <p className="text-sm text-muted-foreground">{t("noImage")}</p>
        )}
        <div className="flex flex-col gap-2">
          <Label htmlFor="groundplan-image">{t("chooseImage")}</Label>
          <Input id="groundplan-image" type="file" accept="image/png,image/jpeg" onChange={handleFileChange} />
        </div>
      </div>

      <div className="flex max-w-2xl flex-col gap-4 rounded-md border p-4">
        <Label className="text-base font-bold underline">{t("boundsLabel")}</Label>
        <p className="text-sm text-muted-foreground">{t("boundsDescription")}</p>
        <div className="grid grid-cols-2 gap-4">
          <div className="flex flex-col gap-2">
            <Label htmlFor="groundplan-sw-lat">{t("swLatitude")}</Label>
            <Input id="groundplan-sw-lat" type="number" step="any" value={swLatitude} onChange={(event) => setSwLatitude(event.target.value)} />
          </div>
          <div className="flex flex-col gap-2">
            <Label htmlFor="groundplan-sw-lng">{t("swLongitude")}</Label>
            <Input id="groundplan-sw-lng" type="number" step="any" value={swLongitude} onChange={(event) => setSwLongitude(event.target.value)} />
          </div>
          <div className="flex flex-col gap-2">
            <Label htmlFor="groundplan-ne-lat">{t("neLatitude")}</Label>
            <Input id="groundplan-ne-lat" type="number" step="any" value={neLatitude} onChange={(event) => setNeLatitude(event.target.value)} />
          </div>
          <div className="flex flex-col gap-2">
            <Label htmlFor="groundplan-ne-lng">{t("neLongitude")}</Label>
            <Input id="groundplan-ne-lng" type="number" step="any" value={neLongitude} onChange={(event) => setNeLongitude(event.target.value)} />
          </div>
        </div>
      </div>

      <Button onClick={handleSave} disabled={isSaving || !hasValidCoordinates} className="self-start">
        {t("save")}
      </Button>
    </div>
  );
}
