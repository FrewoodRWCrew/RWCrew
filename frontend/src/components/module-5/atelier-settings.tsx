"use client";

// Atelier's "Instellingen" screen: the global switch "Polsband verplicht bij
// Ophalen". The wristband scans themselves (webhook, scanners, the received
// messages) are in the Scans module; a line here says so.

import { useState } from "react";
import { useTranslations } from "next-intl";
import { toast } from "sonner";
import { ApiError, getAtelierSettings, saveAtelierSettings } from "@/lib/api";
import type { AtelierSettings as Settings } from "@/lib/types";
import { Card, CardContent } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import { useKeyedLoad } from "@/components/module-4/use-keyed-load";

interface AtelierSettingsScreenProps {
  canEdit: boolean;
}

export function AtelierSettingsScreen({ canEdit }: AtelierSettingsScreenProps) {
  const t = useTranslations("atelier.settings");
  const settings = useKeyedLoad<Settings>("atelier-settings", getAtelierSettings);
  const [isSaving, setIsSaving] = useState(false);

  async function toggleRequired(value: boolean) {
    setIsSaving(true);
    try {
      settings.setData(await saveAtelierSettings(value));
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

      {settings.data && (
        <Card>
          <CardContent className="flex flex-col gap-4">
            <div className="flex items-center gap-3">
              <Checkbox
                id="atelier-wristband-required"
                checked={settings.data.wristband_required}
                disabled={!canEdit || isSaving}
                onCheckedChange={(checked) => void toggleRequired(checked === true)}
              />
              <label htmlFor="atelier-wristband-required" className="font-medium">
                {t("wristbandRequired")}
              </label>
            </div>
            <p className="text-sm text-muted-foreground">{t("wristbandRequiredHelp")}</p>
            <p className="border-t pt-4 text-sm text-muted-foreground">{t("scansElsewhere")}</p>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
