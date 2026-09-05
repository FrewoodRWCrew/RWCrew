"use client";

// MasterData's "Team Tasks" screen (nested under "Teams"): a thin
// wrapper around the shared LookupManagement component (see
// lookup-management.tsx), supplying its own translated labels and
// api.ts functions, plus `field="team_tasks"` since this screen's value
// isn't called "name" like the original five lookup screens.

import { useTranslations } from "next-intl";
import { createTeamTask, deleteTeamTask, updateTeamTask } from "@/lib/api";
import type { TeamTask } from "@/lib/types";
import { LookupManagement } from "@/components/module-9/lookup-management";

interface TeamTaskManagementProps {
  initialTeamTasks: TeamTask[];
}

export function TeamTaskManagement({ initialTeamTasks }: TeamTaskManagementProps) {
  const t = useTranslations("masterdata.teamTasks");
  const tCommon = useTranslations("common");

  return (
    <LookupManagement
      field="team_tasks"
      initialItems={initialTeamTasks}
      create={createTeamTask}
      update={updateTeamTask}
      remove={deleteTeamTask}
      labels={{
        title: t("title"),
        description: t("description"),
        tableName: t("tableName"),
        tableActions: t("tableActions"),
        newItem: t("newTeamTask"),
        nameLabel: t("teamTasksLabel"),
        createTitle: t("createTitle"),
        createDescription: t("createDescription"),
        itemCreated: t("teamTaskCreated"),
        createFailed: t("createFailed"),
        change: t("change"),
        delete: t("delete"),
        changeTitle: t("changeTitle"),
        changeDescription: t("changeDescription"),
        itemUpdated: t("teamTaskUpdated"),
        updateFailed: t("updateFailed"),
        deleteConfirmTitle: t("deleteConfirmTitle"),
        deleteConfirmDescription: (name) => t("deleteConfirmDescription", { name }),
        itemDeleted: t("teamTaskDeleted"),
        deleteFailed: t("deleteFailed"),
        cancel: tCommon("cancel"),
      }}
    />
  );
}
