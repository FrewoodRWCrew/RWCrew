// MasterData's "Festivals per ploeg" screen (nested under "Teams") — see
// TeamFestivalGridScreen for the actual UI. Opens on `?season=<id>` when
// given, else on the backend's default year (the last open one).

import { getTranslations } from "next-intl/server";
import { ServerApiError, serverApiFetch } from "@/lib/server-api";
import type { TeamFestivalGrid, TeamFestivalOptions } from "@/lib/types";
import { TeamFestivalGridScreen } from "@/components/module-9/team-festival-grid";

interface PageProps {
  searchParams: Promise<{ season?: string }>;
}

export default async function MasterDataTeamFestivalsPage({ searchParams }: PageProps) {
  const tErrors = await getTranslations("errors");
  const { season } = await searchParams;

  let options: TeamFestivalOptions;
  let grid: TeamFestivalGrid | null = null;
  try {
    // The year dropdown comes from this screen's own endpoint, so no view
    // right on the Years screen is needed as well.
    options = await serverApiFetch<TeamFestivalOptions>("/api/modules/module-9/team-festivals/options");
    // A year from the address only counts when it exists.
    const requested = options.seasons.find((option) => String(option.id) === season)?.id;
    const seasonId = requested ?? options.default_season_id;
    if (seasonId !== null) {
      grid = await serverApiFetch<TeamFestivalGrid>(`/api/modules/module-9/team-festivals/grid?season_id=${seasonId}`);
    }
  } catch (error) {
    if (error instanceof ServerApiError && error.status === 403) {
      return <p className="text-sm text-destructive">{tErrors("forbidden")}</p>;
    }
    throw error;
  }

  // Keyed by year so switching years through the address starts a fresh draft.
  return <TeamFestivalGridScreen key={grid?.season_id ?? 0} options={options} initialGrid={grid} />;
}
