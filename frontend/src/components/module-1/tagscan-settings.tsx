"use client";

// TagScan's "Settings" screen: lets an admin override the VPS-side CSV
// intake "receive folder" path (falling back to the backend's own .env
// default when nothing's been saved), switch TagScan's automatic background
// Scan on/off and set its interval (see backend module_1/auto_scan.py), and
// shows the device-intake upload
// URL a Raspberry Pi's watcher script should POST to — see
// scripts/pi-watcher/ and app/modules/module_1/device_router.py.

import { useState } from "react";
import { useTranslations } from "next-intl";
import { toast } from "sonner";
import { API_BASE_URL } from "@/lib/config";
import { ApiError, updateTagscanAutoScan, updateTagscanSettings } from "@/lib/api";
import type { TagscanSettings } from "@/lib/types";
import { formatDateTime } from "@/lib/date-time";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

const INTAKE_UPLOAD_URL = `${API_BASE_URL}/api/public/tagscan-intake`;

// Allowed interval range, same as the backend's validation.
const MIN_INTERVAL_SECONDS = 10;
const MAX_INTERVAL_SECONDS = 86400;

interface TagscanSettingsProps {
  initialSettings: TagscanSettings;
}

async function copyToClipboard(value: string, onSuccess: () => void, onError: () => void) {
  try {
    await navigator.clipboard.writeText(value);
    onSuccess();
  } catch {
    onError();
  }
}

export function TagscanSettingsForm({ initialSettings }: TagscanSettingsProps) {
  const t = useTranslations("tagscan.settings");
  const [settings, setSettings] = useState(initialSettings);
  const [path, setPath] = useState(initialSettings.receive_folder_path);
  const [isSaving, setIsSaving] = useState(false);
  const [autoScanEnabled, setAutoScanEnabled] = useState(initialSettings.auto_scan_enabled);
  const [intervalText, setIntervalText] = useState(String(initialSettings.auto_scan_interval_seconds));
  const [isSavingAutoScan, setIsSavingAutoScan] = useState(false);

  const intervalSeconds = Number(intervalText);
  const intervalIsValid =
    Number.isInteger(intervalSeconds) &&
    intervalSeconds >= MIN_INTERVAL_SECONDS &&
    intervalSeconds <= MAX_INTERVAL_SECONDS;

  async function handleSaveAutoScan() {
    setIsSavingAutoScan(true);
    try {
      const updated = await updateTagscanAutoScan({ enabled: autoScanEnabled, interval_seconds: intervalSeconds });
      setSettings(updated);
      setAutoScanEnabled(updated.auto_scan_enabled);
      setIntervalText(String(updated.auto_scan_interval_seconds));
      toast.success(t("autoScanSaved"));
    } catch (error) {
      toast.error(error instanceof ApiError ? error.message : t("autoScanSaveFailed"));
    } finally {
      setIsSavingAutoScan(false);
    }
  }

  async function handleSave() {
    setIsSaving(true);
    try {
      const updated = await updateTagscanSettings({ receive_folder_path: path });
      setSettings(updated);
      setPath(updated.receive_folder_path);
      toast.success(t("saved"));
    } catch (error) {
      toast.error(error instanceof ApiError ? error.message : t("saveFailed"));
    } finally {
      setIsSaving(false);
    }
  }

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight underline">{t("title")}</h1>
        <p className="text-muted-foreground">{t("description")}</p>
      </div>

      <div className="flex max-w-2xl flex-col gap-4 rounded-md border p-4">
        <div className="flex items-center gap-2">
          <Label className="text-base font-bold underline">{t("receiveFolderLabel")}</Label>
          <Badge variant={settings.is_override ? "default" : "secondary"}>
            {settings.is_override ? t("customValue") : t("defaultValue")}
          </Badge>
        </div>
        <p className="text-sm text-muted-foreground">{t("receiveFolderDescription")}</p>
        <div className="flex gap-2">
          <Input value={path} onChange={(event) => setPath(event.target.value)} className="font-mono text-sm" />
          <Button onClick={handleSave} disabled={isSaving || !path.trim()}>
            {t("save")}
          </Button>
        </div>
      </div>

      {/* Automatic background Scan: on/off + interval, and when it last ran. */}
      <div className="flex max-w-2xl flex-col gap-4 rounded-md border p-4">
        <Label className="text-base font-bold underline">{t("autoScanTitle")}</Label>
        <p className="text-sm text-muted-foreground">{t("autoScanDescription")}</p>
        <label className="flex items-center gap-2 text-sm font-medium">
          <Checkbox checked={autoScanEnabled} onCheckedChange={(checked) => setAutoScanEnabled(checked === true)} />
          {t("autoScanEnabledLabel")}
        </label>
        <div className="flex flex-wrap items-end gap-2">
          <div className="flex flex-col gap-2">
            <Label htmlFor="tagscan-auto-scan-interval">{t("autoScanIntervalLabel")}</Label>
            <Input
              id="tagscan-auto-scan-interval"
              type="number"
              min={MIN_INTERVAL_SECONDS}
              max={MAX_INTERVAL_SECONDS}
              step={1}
              className="w-40"
              value={intervalText}
              disabled={!autoScanEnabled}
              aria-invalid={!intervalIsValid}
              onChange={(event) => setIntervalText(event.target.value)}
            />
          </div>
          <Button onClick={handleSaveAutoScan} disabled={isSavingAutoScan || !intervalIsValid}>
            {t("save")}
          </Button>
        </div>
        {!intervalIsValid && (
          <p className="text-sm text-destructive">
            {t("autoScanIntervalInvalid", { min: MIN_INTERVAL_SECONDS, max: MAX_INTERVAL_SECONDS })}
          </p>
        )}
        <p className="text-sm text-muted-foreground">
          {settings.last_auto_scan_at
            ? t("lastAutoScan", {
                when: formatDateTime(settings.last_auto_scan_at),
                summary: settings.last_auto_scan_summary ?? "",
              })
            : t("autoScanNeverRun")}
        </p>
      </div>

      <div className="flex max-w-2xl flex-col gap-2 rounded-md border p-4">
        <Label className="text-base font-bold underline">{t("uploadUrlLabel")}</Label>
        <p className="text-sm text-muted-foreground">{t("uploadUrlDescription")}</p>
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
        <p className="text-sm text-muted-foreground">{t("uploadUrlHint")}</p>
      </div>
    </div>
  );
}
