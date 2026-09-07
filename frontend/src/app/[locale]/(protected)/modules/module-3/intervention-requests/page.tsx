// Intervention Requests' main screen: a table of requests with add/
// change/delete — see InterventionRequestsManagement for the actual UI.

import { getTranslations } from "next-intl/server";
import { ServerApiError, serverApiFetch } from "@/lib/server-api";
import type {
  InterventionRequest,
  InterventionRequestsTeam,
  InterventionStatus,
  TeamKarMemberOption,
} from "@/lib/types";
import { InterventionRequestsManagement } from "@/components/module-3/intervention-requests-management";

export default async function InterventionRequestsPage() {
  const tErrors = await getTranslations("errors");

  let requests: InterventionRequest[] | null = null;
  let statuses: InterventionStatus[] = [];
  let teams: InterventionRequestsTeam[] = [];
  let teamKarMembers: TeamKarMemberOption[] = [];
  try {
    requests = await serverApiFetch<InterventionRequest[]>("/api/modules/module-3/intervention-requests");
    // Fetched here too since a user might be able to manage requests
    // without also being able to open the Intervention Statuses screen
    // directly — the same reasoning products/page.tsx uses for its own
    // lookup lists.
    statuses = await serverApiFetch<InterventionStatus[]>("/api/modules/module-3/intervention-statuses").catch(
      () => [],
    );
    // The "Ploeg" dropdown's options — module-3's own lightweight read of
    // MasterData_team (not MasterData's own endpoint), so it's available
    // regardless of the user's MasterData role.
    teams = await serverApiFetch<InterventionRequestsTeam[]>("/api/modules/module-3/teams").catch(() => []);
    // The "Team Kar" dropdown's options — current TeamKar members, read via
    // module-3's own lightweight endpoint, available regardless of the
    // user's TeamKar permission.
    teamKarMembers = await serverApiFetch<TeamKarMemberOption[]>("/api/modules/module-3/teamkar/options").catch(
      () => [],
    );
  } catch (error) {
    if (error instanceof ServerApiError && error.status === 403) {
      return <p className="text-sm text-destructive">{tErrors("forbidden")}</p>;
    }
    throw error;
  }

  return (
    <InterventionRequestsManagement
      initialRequests={requests}
      statuses={statuses}
      teams={teams}
      teamKarMembers={teamKarMembers}
    />
  );
}
