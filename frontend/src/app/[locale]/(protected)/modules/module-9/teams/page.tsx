// MasterData's "Teams" screen: a table of teams with add/change/delete,
// matching the field set of the reference "Teams" edit screen — see
// TeamManagement for the actual UI.

import { getTranslations } from "next-intl/server";
import { ServerApiError, serverApiFetch } from "@/lib/server-api";
import type { AltsienKernlid, DeliveryMethod, Team, TeamLocation, TeamTask } from "@/lib/types";
import { TeamManagement } from "@/components/module-9/team-management";

export default async function MasterDataTeamsPage() {
  const tErrors = await getTranslations("errors");

  let teams: Team[] | null = null;
  let teamLocations: TeamLocation[] = [];
  let deliveryMethods: DeliveryMethod[] = [];
  let teamTasks: TeamTask[] = [];
  let kernleden: AltsienKernlid[] = [];
  try {
    teams = await serverApiFetch<Team[]>("/api/modules/module-9/teams");
    // These four lookup lists power the Locatie/Leverwijze/Taken/Kernleden
    // fields on the create/edit form — fetched here too since a user might
    // be able to manage teams without also being able to view those
    // screens directly.
    [teamLocations, deliveryMethods, teamTasks, kernleden] = await Promise.all([
      serverApiFetch<TeamLocation[]>("/api/modules/module-9/team-locations").catch(() => []),
      serverApiFetch<DeliveryMethod[]>("/api/modules/module-9/delivery-methods").catch(() => []),
      serverApiFetch<TeamTask[]>("/api/modules/module-9/team-tasks").catch(() => []),
      serverApiFetch<AltsienKernlid[]>("/api/modules/module-9/altsien-kernleden").catch(() => []),
    ]);
  } catch (error) {
    if (error instanceof ServerApiError && error.status === 403) {
      return <p className="text-sm text-destructive">{tErrors("forbidden")}</p>;
    }
    throw error;
  }

  return (
    <TeamManagement
      initialTeams={teams}
      teamLocations={teamLocations}
      deliveryMethods={deliveryMethods}
      teamTasks={teamTasks}
      kernleden={kernleden}
    />
  );
}
