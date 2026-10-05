"use client";

// StockMaster's own season dropdown (the same idea as Altsien Select's):
// it lists every season, open and closed, so last season's bookings and
// needs stay viewable. It starts on the header's selected season (or the
// first open one), and the choice travels between StockMaster screens in
// the "?season=" URL parameter.

import { useTranslations } from "next-intl";
import { usePathname, useRouter } from "@/i18n/navigation";
import { useSearchParams } from "next/navigation";
import type { Season } from "@/lib/types";
import { useSelectedSeason } from "@/components/shared/season-provider";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";

/** The season StockMaster's screens should use: the one in the URL, else
 *  the header's choice, else the last open season, else the last one. */
export function useStockMasterSeasonId(seasons: Season[]): number | null {
  const searchParams = useSearchParams();
  const { selectedSeasonId } = useSelectedSeason();

  const fromUrl = Number(searchParams.get("season"));
  if (fromUrl && seasons.some((season) => season.id === fromUrl)) {
    return fromUrl;
  }
  if (selectedSeasonId !== null && seasons.some((season) => season.id === selectedSeasonId)) {
    return selectedSeasonId;
  }
  const open = seasons.filter((season) => season.periode_open);
  return (open[open.length - 1] ?? seasons[seasons.length - 1])?.id ?? null;
}

interface StockMasterSeasonSelectProps {
  seasons: Season[];
  seasonId: number | null;
}

export function StockMasterSeasonSelect({ seasons, seasonId }: StockMasterSeasonSelectProps) {
  const t = useTranslations("stockMaster.common");
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();

  // Store the choice in the URL, keeping any other parameters (e.g. ?kar=).
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

  function seasonLabel(season: Season) {
    return season.periode_open ? season.name : `${season.name} (${t("seasonClosed")})`;
  }

  return (
    <div className="flex w-44 flex-col gap-2">
      <Label htmlFor="stockmaster-season">{t("seasonLabel")}</Label>
      <Select value={seasonId !== null ? String(seasonId) : ""} onValueChange={handleChange}>
        <SelectTrigger id="stockmaster-season">
          <SelectValue>
            {(value: string | null) => {
              const season = seasons.find((item) => String(item.id) === value);
              return season ? seasonLabel(season) : t("noSeason");
            }}
          </SelectValue>
        </SelectTrigger>
        <SelectContent>
          {seasons.map((season) => (
            <SelectItem key={season.id} value={String(season.id)}>
              {seasonLabel(season)}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  );
}
