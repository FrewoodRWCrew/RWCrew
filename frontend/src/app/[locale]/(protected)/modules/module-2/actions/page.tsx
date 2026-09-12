// KarTracker's "Actions" screen — a placeholder for now (see
// kartracker-sidebar.tsx for the gated sidebar link). No data to load yet,
// so this just shows a short "coming soon" card the same way the landing
// page (.../module-2/page.tsx) does.

import { getTranslations } from "next-intl/server";
import { getModuleTheme } from "@/lib/module-theme";
import { cn } from "@/lib/utils";

export default async function KarTrackerActionsPage() {
  const t = await getTranslations("karTracker");
  const tActions = await getTranslations("karTracker.actions");
  const theme = getModuleTheme("module-2");

  return (
    <div className="flex flex-col gap-4">
      <div className={cn("inline-flex w-fit items-center rounded-full px-3 py-1 text-xs font-medium", theme.badgeClassName)}>
        {t("moduleTitle")}
      </div>
      <h1 className="text-2xl font-bold tracking-tight underline">{tActions("title")}</h1>
      <p className="text-muted-foreground">{tActions("description")}</p>
    </div>
  );
}
