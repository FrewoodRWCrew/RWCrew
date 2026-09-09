// KarTracker's landing page. Access is already gated by this route's own
// layout.tsx (a 403 there shows the forbidden message before this ever
// renders), so this just shows a short "more is coming" card — there's no
// KPI dashboard yet since there's no business data to aggregate. This is
// the module's first development phase; a real dashboard gets built here
// once the cart registry ("Karlijst") and delivery planning screens exist.

import { getTranslations } from "next-intl/server";
import { getModuleTheme } from "@/lib/module-theme";
import { cn } from "@/lib/utils";

export default async function KarTrackerLandingPage() {
  const t = await getTranslations("karTracker");
  const tLanding = await getTranslations("karTracker.landing");
  const theme = getModuleTheme("module-2");

  return (
    <div className="flex flex-col gap-4">
      <div className={cn("inline-flex w-fit items-center rounded-full px-3 py-1 text-xs font-medium", theme.badgeClassName)}>
        {t("moduleTitle")}
      </div>
      <h1 className="text-2xl font-bold tracking-tight underline">{tLanding("title")}</h1>
      <p className="text-muted-foreground">{tLanding("description")}</p>
    </div>
  );
}
