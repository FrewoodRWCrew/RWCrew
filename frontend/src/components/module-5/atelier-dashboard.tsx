// Atelier's landing dashboard ("KPI overzicht"): the "Balie" section (pieces
// handed out today, not returned yet), the "Masterdata" section (catalogue counts), the "Reservaties" section (per
// festival of a season: persons, pieces per day, teams without package), the
// "Stock" section (pieces per status, sizes below their minimum), the
// "Gewassen" section (pieces washed per day / festival / season) and a notice
// about the blocks still to come.

import { Shirt } from "lucide-react";
import { getTranslations } from "next-intl/server";
import { getModuleTheme } from "@/lib/module-theme";
import type { Season } from "@/lib/types";
import { cn } from "@/lib/utils";
import { Card, CardContent } from "@/components/ui/card";
import { DeskStatsSection } from "@/components/module-5/desk-stats-section";
import { MasterdataStatsSection } from "@/components/module-5/masterdata-stats-section";
import { ReservationStatsSection } from "@/components/module-5/reservation-stats-section";
import { StockTotalsSection } from "@/components/module-5/stock-totals-section";
import { WashStatsSection } from "@/components/module-5/wash-stats-section";

interface AtelierDashboardProps {
  seasons: Season[];
}

export async function AtelierDashboard({ seasons }: AtelierDashboardProps) {
  const t = await getTranslations("atelier.landing");
  // The soft pill colours of this module's accent, for the notice's icon.
  const { badgeClassName } = getModuleTheme("module-5");

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight underline">{t("title")}</h1>
        <p className="text-muted-foreground">{t("description")}</p>
      </div>

      <DeskStatsSection />

      <MasterdataStatsSection />

      <ReservationStatsSection seasons={seasons} />

      <StockTotalsSection />

      <WashStatsSection seasons={seasons} />

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
