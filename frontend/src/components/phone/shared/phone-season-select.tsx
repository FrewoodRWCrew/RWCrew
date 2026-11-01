"use client";

// The phone home page's year picker, the phone version of the desktop
// header's SeasonSelector: a searchable dropdown bound to the same
// SeasonProvider. A module tile only opens once a year is chosen
// (see phone-tile-grid.tsx). Renders nothing when there are no open years.

import { useTranslations } from "next-intl";
import { Label } from "@/components/ui/label";
import { SearchableSelect } from "@/components/ui/searchable-select";
import { useSelectedSeason } from "@/components/shared/season-provider";

export function PhoneSeasonSelect() {
  const t = useTranslations("seasonSelector");
  const { seasons, selectedSeasonId, setSelectedSeasonId } = useSelectedSeason();

  if (seasons.length === 0) {
    return null;
  }

  return (
    <div className="flex flex-col gap-2">
      <Label htmlFor="phone-season">{t("label")}</Label>
      <SearchableSelect
        id="phone-season"
        size="phone"
        value={selectedSeasonId === null ? null : String(selectedSeasonId)}
        onValueChange={(value) => setSelectedSeasonId(Number(value))}
        placeholder={t("placeholder")}
        options={seasons.map((season) => ({ value: String(season.id), label: season.name }))}
      />
    </div>
  );
}
