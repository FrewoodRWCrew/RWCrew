// MasterData's "Team Tasks" screen (nested under "Teams") — see
// TeamTaskManagement for the actual UI.

import { getTranslations } from "next-intl/server";
import { ServerApiError, serverApiFetch } from "@/lib/server-api";
import type { TeamTask } from "@/lib/types";
import { TeamTaskManagement } from "@/components/module-9/team-task-management";

export default async function MasterDataTeamTasksPage() {
  const tErrors = await getTranslations("errors");

  let teamTasks: TeamTask[] | null = null;
  try {
    teamTasks = await serverApiFetch<TeamTask[]>("/api/modules/module-9/team-tasks");
  } catch (error) {
    if (error instanceof ServerApiError && error.status === 403) {
      return <p className="text-sm text-destructive">{tErrors("forbidden")}</p>;
    }
    throw error;
  }

  return <TeamTaskManagement initialTeamTasks={teamTasks} />;
}
