"use client";

// KarTracker's "Karcode Simulator" web screen (screen key
// "kartracker.karcodesimulator"): the page heading plus the calculator
// (karcode-calculator.tsx), which the phone app shows too.

import { useTranslations } from "next-intl";
import { KarcodeCalculator } from "@/components/module-2/karcode-calculator";

export function KarcodeSimulator() {
  const t = useTranslations("karTracker.karcodeSimulator");

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight underline">{t("title")}</h1>
        <p className="text-muted-foreground">{t("description")}</p>
      </div>
      <KarcodeCalculator variant="desktop" />
    </div>
  );
}
