// Atelier's landing dashboard ("KPI overzicht"). For now the module is only
// a shell, so this shows the page title and a "coming in phase 2" notice;
// the stat tiles and charts about the clothing handed out and returned, and the stock come here once those screens
// exist (see Altsien Select's or StockMaster's dashboard for the pattern).

import { Shirt } from "lucide-react";
import { getTranslations } from "next-intl/server";
import { getModuleTheme } from "@/lib/module-theme";
import { cn } from "@/lib/utils";
import { Card, CardContent } from "@/components/ui/card";

export async function AtelierDashboard() {
  const t = await getTranslations("atelier.landing");
  // The soft pill colours of this module's accent, for the notice's icon.
  const { badgeClassName } = getModuleTheme("module-5");

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight underline">{t("title")}</h1>
        <p className="text-muted-foreground">{t("description")}</p>
      </div>

      <Card>
        <CardContent className="flex items-center gap-4">
          <div className={cn("flex size-12 shrink-0 items-center justify-center rounded-full", badgeClassName)}>
            <Shirt className="size-6" />
          </div>
          <div>
            <p className="font-medium">{t("comingSoonTitle")}</p>
            <p className="text-sm text-muted-foreground">{t("comingSoon")}</p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
