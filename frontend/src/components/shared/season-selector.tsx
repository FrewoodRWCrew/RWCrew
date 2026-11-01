"use client";

// The header's season dropdown: lets the visitor pick which (open) season
// they're currently working in — see season-provider.tsx for where the
// list and the persisted selection actually live. Renders nothing at all
// when there are no open seasons to choose from, which also covers users
// who can't see the Season screen (the protected layout fetches an empty
// list for them instead of erroring).

import { useTranslations } from "next-intl";
import { SearchableSelect } from "@/components/ui/searchable-select";
import { useSelectedSeason } from "@/components/shared/season-provider";

export function SeasonSelector() {
  const t = useTranslations("seasonSelector");
  const { seasons, selectedSeasonId, setSelectedSeasonId } = useSelectedSeason();

  if (seasons.length === 0) {
    return null;
  }

  return (
    <SearchableSelect
      value={selectedSeasonId !== null ? String(selectedSeasonId) : ""}
      onValueChange={(value) => setSelectedSeasonId(value ? Number(value) : null)}
      size="sm"
      aria-label={t("label")}
      title={t("label")}
      renderValue={(value: string | null) =>
        (value ? seasons.find((season) => String(season.id) === value)?.name : t("placeholder"))
      }
      options={seasons.map((season) => ({ value: String(season.id), label: season.name }))}
    />
  );
}
