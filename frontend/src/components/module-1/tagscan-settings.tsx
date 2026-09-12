"use client";

// TagScan's "Settings" screen: lets an admin override the VPS-side CSV
// intake "receive folder" path (falling back to the backend's own .env
// default when nothing's been saved), and shows the device-intake upload
// URL a Raspberry Pi's watcher script should POST to — see
// scripts/pi-watcher/ and app/modules/module_1/device_router.py.

import { useState } from "react";
import { useTranslations } from "next-intl";
import { toast } from "sonner";
import { API_BASE_URL } from "@/lib/config";
import { ApiError, updateTagscanSettings } from "@/lib/api";
import type { TagscanSettings } from "@/lib/types";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

const INTAKE_UPLOAD_URL = `${API_BASE_URL}/api/public/tagscan-intake`;

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

  async function handleSave() {
    setIsSaving(true);
    try {
      const updated = await updateTagscanSettings({ receive_folder_path: path, is_override: true });
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
