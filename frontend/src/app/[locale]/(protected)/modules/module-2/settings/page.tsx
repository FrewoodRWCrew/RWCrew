// KarTracker's "Instellingen" screen (screen key "kartracker.settings"):
// module-wide settings, for now the karcode formula — see KarTrackerSettingsForm
// for the actual UI. "Edit" on the screen decides whether the formula can be
// saved (the backend enforces the same rule). Sidebar visibility is gated by
// canViewSettings in kartracker-sidebar.tsx.

import { getTranslations } from "next-intl/server";
import { ServerApiError, serverApiFetch } from "@/lib/server-api";
import type { KarTrackerMyPermissions, KarTrackerSettings } from "@/lib/types";
import { KarTrackerSettingsForm } from "@/components/module-2/kartracker-settings";

export default async function KarTrackerSettingsPage() {
  const tErrors = await getTranslations("errors");

  let permissions: KarTrackerMyPermissions;
  let settings: KarTrackerSettings;
  try {
    [permissions, settings] = await Promise.all([
      serverApiFetch<KarTrackerMyPermissions>(
        "/api/modules/module-2/me/permissions",
      ),
      serverApiFetch<KarTrackerSettings>("/api/modules/module-2/settings"),
    ]);
  } catch (error) {
    if (error instanceof ServerApiError && error.status === 403) {
      return <p className="text-sm text-destructive">{tErrors("forbidden")}</p>;
    }
    throw error;
  }

  return (
    <KarTrackerSettingsForm
      initialSettings={settings}
      canEdit={permissions.editable_screen_keys.includes("kartracker.settings")}
    />
  );
}
