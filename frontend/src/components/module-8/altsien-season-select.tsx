"use client";

// Altsien Select's own season dropdown, used at the top of the KPI screen,
// the Ploeg Wizard, the Ploegfiche and the request follow-up. Unlike the
// header's season selector (which only lists seasons whose period is open),
// this lists every season, so a team's choices from an earlier, closed
// season stay viewable. It starts on the header's selected season (or the
// first open one), and the choice travels between Altsien Select screens in
// the "?season=" URL parameter.

import { useTranslations } from "next-intl";
import { usePathname, useRouter } from "@/i18n/navigation";
import { useSearchParams } from "next/navigation";
import type { Season } from "@/lib/types";
import { useSelectedSeason } from "@/components/shared/season-provider";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";

/** The season Altsien Select's screens should show: the one in the URL,
 *  else the header's choice, else the first open season, else the first. */
export function useAltsienSeasonId(seasons: Season[]): number | null {
  const searchParams = useSearchParams();
  const { selectedSeasonId } = useSelectedSeason();

  const fromUrl = Number(searchParams.get("season"));
  if (fromUrl && seasons.some((season) => season.id === fromUrl)) {
    return fromUrl;
  }
  if (selectedSeasonId !== null && seasons.some((season) => season.id === selectedSeasonId)) {
    return selectedSeasonId;
  }
  return (seasons.find((season) => season.periode_open) ?? seasons[0])?.id ?? null;
}

interface AltsienSeasonSelectProps {
  seasons: Season[];
  seasonId: number | null;
}

export function AltsienSeasonSelect({ seasons, seasonId }: AltsienSeasonSelectProps) {
  const t = useTranslations("altsienSelect.common");
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();

  // Store the choice in the URL, keeping any other parameters (e.g. ?team=).
  function handleChange(value: string | null) {
    const params = new URLSearchParams(searchParams.toString());
    if (value) {
      params.set("season", value);
    } else {
      params.delete("season");
    }
    const query = params.toString();
    router.replace(query ? `${pathname}?${query}` : pathname);
  }

  return (
    <div className="flex max-w-xs flex-col gap-2">
      <Label htmlFor="altsien-season">{t("seasonLabel")}</Label>
      <Select value={seasonId !== null ? String(seasonId) : ""} onValueChange={handleChange}>
        <SelectTrigger id="altsien-season">
          <SelectValue>
            {(value: string | null) => {
              const season = seasons.find((item) => String(item.id) === value);
              if (!season) return t("noSeason");
              return season.periode_open ? season.name : `${season.name} (${t("seasonClosed")})`;
            }}
          </SelectValue>
        </SelectTrigger>
        <SelectContent>
          {seasons.map((season) => (
            <SelectItem key={season.id} value={String(season.id)}>
              {season.periode_open ? season.name : `${season.name} (${t("seasonClosed")})`}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  );
}
