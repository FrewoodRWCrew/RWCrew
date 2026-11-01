// TagScan's "Settings" screen: the receive-folder path override + the
// device-intake upload URL, plus the wristbands' webhook details — see
// TagscanSettingsForm for the actual UI.

import { getTranslations } from "next-intl/server";
import { ServerApiError, serverApiFetch } from "@/lib/server-api";
import type { TagscanMyPermissions, TagscanSettings, WristbandSettings } from "@/lib/types";
import { TagscanSettingsForm } from "@/components/module-1/tagscan-settings";

export default async function TagscanSettingsPage() {
  const tErrors = await getTranslations("errors");

  let settings: TagscanSettings | null = null;
  let wristband: WristbandSettings | null = null;
  let permissions: TagscanMyPermissions | null = null;
  try {
    [settings, wristband, permissions] = await Promise.all([
      serverApiFetch<TagscanSettings>("/api/modules/module-1/settings"),
      serverApiFetch<WristbandSettings>("/api/modules/module-1/wristband/settings"),
      serverApiFetch<TagscanMyPermissions>("/api/modules/module-1/me/permissions"),
    ]);
  } catch (error) {
    if (error instanceof ServerApiError && error.status === 403) {
      return <p className="text-sm text-destructive">{tErrors("forbidden")}</p>;
    }
    throw error;
  }

  return (
    <TagscanSettingsForm
      initialSettings={settings}
      wristband={wristband}
      canEditWristband={permissions.editable_screen_keys.includes("tagscan.settings")}
    />
  );
}
