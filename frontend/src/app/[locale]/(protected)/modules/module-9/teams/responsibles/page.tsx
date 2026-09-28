// MasterData's "Ploegverantwoordelijken" screen (nested under "Teams") —
// see TeamResponsibleManagement for the actual UI.

import { getTranslations } from "next-intl/server";
import { ServerApiError, serverApiFetch } from "@/lib/server-api";
import type { TeamResponsible, TeamResponsibleOptions } from "@/lib/types";
import { TeamResponsibleManagement } from "@/components/module-9/team-responsible-management";

export default async function MasterDataTeamResponsiblesPage() {
  const tErrors = await getTranslations("errors");

  let data: [TeamResponsible[], TeamResponsibleOptions];
  try {
    // The team/season dropdown choices come from this screen's own
    // endpoint, so no view rights on Teams/Season are needed as well.
    data = await Promise.all([
      serverApiFetch<TeamResponsible[]>("/api/modules/module-9/team-responsibles"),
      serverApiFetch<TeamResponsibleOptions>("/api/modules/module-9/team-responsibles/options"),
    ]);
  } catch (error) {
    if (error instanceof ServerApiError && error.status === 403) {
      return <p className="text-sm text-destructive">{tErrors("forbidden")}</p>;
    }
    throw error;
  }
  const [teamResponsibles, options] = data;

  return (
    <TeamResponsibleManagement
      initialTeamResponsibles={teamResponsibles}
      teams={options.teams}
      seasons={options.seasons}
    />
  );
}
