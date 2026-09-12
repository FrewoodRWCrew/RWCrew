// KarTracker's "Actions" screen — placeholder until delivery planning is
// designed. Page-level access is enforced by module-2/layout.tsx's module
// access check; sidebar visibility is gated by canViewActions in
// kartracker-sidebar.tsx.

import { getTranslations } from "next-intl/server";

export default async function KarTrackerActionsPage() {
  const t = await getTranslations("karTracker.actions");

  return (
    <div className="flex flex-col gap-4">
      <h1 className="text-2xl font-semibold tracking-tight">{t("title")}</h1>
      <p className="text-muted-foreground">{t("comingSoon")}</p>
    </div>
  );
}
