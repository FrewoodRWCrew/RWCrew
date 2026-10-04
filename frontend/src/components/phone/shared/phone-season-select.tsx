"use client";

// The phone home page's year picker, the phone version of the desktop
// header's SeasonSelector: a native <select> (the system's own picker) bound
// to the same SeasonProvider. A module tile only opens once a year is chosen
// (see phone-tile-grid.tsx). Renders nothing when there are no open years.

import { useTranslations } from "next-intl";
import { Label } from "@/components/ui/label";
import { useSelectedSeason } from "@/components/shared/season-provider";
import { PhoneSelect } from "@/components/phone/shared/phone-select";

// The "nothing chosen yet" entry (a <select> value is always a string).
const NO_SEASON_VALUE = "";

export function PhoneSeasonSelect() {
  const t = useTranslations("seasonSelector");
  const { seasons, selectedSeasonId, setSelectedSeasonId } = useSelectedSeason();

  if (seasons.length === 0) {
    return null;
  }

  return (
    <div className="flex flex-col gap-2">
      <Label htmlFor="phone-season">{t("label")}</Label>
      <PhoneSelect
        id="phone-season"
        value={selectedSeasonId ?? NO_SEASON_VALUE}
        onChange={(event) =>
          setSelectedSeasonId(event.target.value === NO_SEASON_VALUE ? null : Number(event.target.value))
        }
      >
        {/* The empty entry only shows while nothing is chosen yet. */}
        {selectedSeasonId === null && <option value={NO_SEASON_VALUE}>{t("placeholder")}</option>}
        {seasons.map((season) => (
          <option key={season.id} value={season.id}>
            {season.name}
          </option>
        ))}
      </PhoneSelect>
    </div>
  );
}
