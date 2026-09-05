// MasterData's "Team Location" screen (nested under "Teams") — see
// TeamLocationManagement for the actual UI.

import { getTranslations } from "next-intl/server";
import { ServerApiError, serverApiFetch } from "@/lib/server-api";
import type { TeamLocation } from "@/lib/types";
import { TeamLocationManagement } from "@/components/module-9/team-location-management";

export default async function MasterDataTeamLocationPage() {
  const tErrors = await getTranslations("errors");

  let teamLocations: TeamLocation[] | null = null;
  try {
    teamLocations = await serverApiFetch<TeamLocation[]>("/api/modules/module-9/team-locations");
  } catch (error) {
    if (error instanceof ServerApiError && error.status === 403) {
      return <p className="text-sm text-destructive">{tErrors("forbidden")}</p>;
    }
    throw error;
  }

  return <TeamLocationManagement initialTeamLocations={teamLocations} />;
}
