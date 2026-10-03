"use client";

// The movement form for one scanned kar: pick its new status (pre-filled
// with the current one) while the phone's GPS position is taken
// automatically, then "Beweging opslaan". The backend adds the kar's team
// and the time, exactly like the desktop "Manuele kar beweging" screen.

import { useCallback, useEffect, useState } from "react";
import { LocateFixed } from "lucide-react";
import { useTranslations } from "next-intl";
import { toast } from "sonner";
import { useRouter } from "@/i18n/navigation";
import { ApiError, createKarAction } from "@/lib/api";
import type { KarTrackerKarActionKarOption, KarTrackerPlanKarOption } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { karTrackerPhoneRoutes } from "@/components/phone/module-2/kartracker-phone-routes";
import { PhoneSelect } from "@/components/phone/shared/phone-select";

// Same GPS settings as the old phone app: most precise fix, 15 s at most,
// never a cached position.
const GPS_OPTIONS: PositionOptions = { enableHighAccuracy: true, timeout: 15000, maximumAge: 0 };

interface GpsFix {
  latitude: number;
  longitude: number;
  /** How precise the fix is, in metres. */
  accuracy: number;
}

// Why a GPS fix failed, each with its own message.
type GpsFailure = "gpsDenied" | "gpsTimeout" | "gpsFailed";

/** Ask the phone once for its position; rejects with the GpsFailure kind. */
function requestGpsFix(): Promise<GpsFix> {
  return new Promise((resolve, reject: (failure: GpsFailure) => void) => {
    if (!("geolocation" in navigator)) {
      reject("gpsFailed");
      return;
    }
    navigator.geolocation.getCurrentPosition(
      (result) =>
        resolve({
          latitude: result.coords.latitude,
          longitude: result.coords.longitude,
          accuracy: result.coords.accuracy,
        }),
      (error) => {
        if (error.code === error.PERMISSION_DENIED) reject("gpsDenied");
        else if (error.code === error.TIMEOUT) reject("gpsTimeout");
        else reject("gpsFailed");
      },
      GPS_OPTIONS,
    );
  });
}

interface KarMovementFormProps {
  kar: KarTrackerKarActionKarOption;
  statuses: KarTrackerPlanKarOption[];
}

export function KarMovementForm({ kar, statuses }: KarMovementFormProps) {
  const t = useTranslations("karTracker.phone.kar");
  const router = useRouter();
  const [statusId, setStatusId] = useState<number>(kar.status_id);
  const [position, setPosition] = useState<GpsFix | null>(null);
  // Starts "busy": the first GPS fix is requested as soon as the form opens.
  const [isLocating, setIsLocating] = useState(true);
  const [gpsError, setGpsError] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);

  // Ask for a GPS fix and show the result (or why it failed) once it arrives.
  const locate = useCallback(() => {
    requestGpsFix()
      .then((fix) => setPosition(fix))
      .catch((failure: GpsFailure) => setGpsError(t(failure)))
      .finally(() => setIsLocating(false));
  }, [t]);

  // Take the first GPS fix automatically when the form opens.
  useEffect(() => {
    locate();
  }, [locate]);

  // "Locatie opnieuw bepalen".
  function handleRefreshLocation() {
    setIsLocating(true);
    setGpsError(null);
    locate();
  }

  async function handleSave() {
    if (position === null) return;
    setIsSaving(true);
    try {
      await createKarAction({
        kar_id: kar.id,
        status_id: statusId,
        latitude: position.latitude,
        longitude: position.longitude,
      });
      toast.success(t("saveSuccess", { kar: kar.kar_nummer }));
      // Ready for the next kar.
      router.push(karTrackerPhoneRoutes.scan);
    } catch (error) {
      toast.error(error instanceof ApiError ? `${t("saveError")} ${error.message}` : t("saveError"));
      setIsSaving(false);
    }
  }

  const canSave = position !== null && !isLocating && !isSaving;

  return (
    <div className="flex flex-col gap-4">
      {/* The kar's status after the movement. */}
      <div className="flex flex-col gap-2">
        <Label htmlFor="phone-kar-status">{t("statusLabel")}</Label>
        <PhoneSelect id="phone-kar-status" value={statusId} onChange={(event) => setStatusId(Number(event.target.value))}>
          {statuses.map((karStatus) => (
            <option key={karStatus.id} value={karStatus.id}>
              {karStatus.name}
            </option>
          ))}
        </PhoneSelect>
      </div>

      {/* The GPS position, taken automatically; can be asked again. */}
      <div className="flex flex-col gap-2">
        <Label>{t("locationLabel")}</Label>
        {isLocating ? (
          <p className="text-sm text-muted-foreground">{t("locating")}</p>
        ) : position ? (
          <p className="text-sm">
            <span className="tabular-nums">
              {position.latitude.toFixed(6)}, {position.longitude.toFixed(6)}
            </span>
            <span className="block text-xs text-muted-foreground">
              {t("accuracy", { meters: Math.round(position.accuracy) })}
            </span>
          </p>
        ) : null}
        {gpsError && <p className="text-sm text-destructive">{gpsError}</p>}
        <Button type="button" variant="outline" className="h-11 text-base" onClick={handleRefreshLocation} disabled={isLocating}>
          <LocateFixed className="size-4" />
          {t("refreshLocation")}
        </Button>
      </div>

      <Button className="h-12 text-base" onClick={handleSave} disabled={!canSave}>
        {isSaving ? t("saving") : t("save")}
      </Button>
    </div>
  );
}
