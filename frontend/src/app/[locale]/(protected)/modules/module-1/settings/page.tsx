// TagScan's "Settings" screen: the receive-folder path override + the
// device-intake upload URL — see TagscanSettingsForm for the actual UI.

import { getTranslations } from "next-intl/server";
import { ServerApiError, serverApiFetch } from "@/lib/server-api";
import type { TagscanSettings } from "@/lib/types";
import { TagscanSettingsForm } from "@/components/module-1/tagscan-settings";

export default async function TagscanSettingsPage() {
  const tErrors = await getTranslations("errors");

  let settings: TagscanSettings | null = null;
  try {
    settings = await serverApiFetch<TagscanSettings>("/api/modules/module-1/settings");
  } catch (error) {
    if (error instanceof ServerApiError && error.status === 403) {
      return <p className="text-sm text-destructive">{tErrors("forbidden")}</p>;
    }
    throw error;
  }

  return <TagscanSettingsForm initialSettings={settings} />;
}
