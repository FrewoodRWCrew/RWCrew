"use client";

// MasterData's "Team Location" screen (nested under "Teams"): a thin
// wrapper around the shared LookupManagement component (see
// lookup-management.tsx), supplying its own translated labels and
// api.ts functions, plus `field="location"` since this screen's value
// isn't called "name" like the original five lookup screens.

import { useTranslations } from "next-intl";
import { createTeamLocation, deleteTeamLocation, updateTeamLocation } from "@/lib/api";
import type { TeamLocation } from "@/lib/types";
import { LookupManagement } from "@/components/module-9/lookup-management";

interface TeamLocationManagementProps {
  initialTeamLocations: TeamLocation[];
}

export function TeamLocationManagement({ initialTeamLocations }: TeamLocationManagementProps) {
  const t = useTranslations("masterdata.teamLocation");
  const tCommon = useTranslations("common");

  return (
    <LookupManagement
      field="location"
      initialItems={initialTeamLocations}
      create={createTeamLocation}
      update={updateTeamLocation}
      remove={deleteTeamLocation}
      labels={{
        title: t("title"),
        description: t("description"),
        tableName: t("tableName"),
        tableActions: t("tableActions"),
        newItem: t("newTeamLocation"),
        nameLabel: t("locationLabel"),
        createTitle: t("createTitle"),
        createDescription: t("createDescription"),
        itemCreated: t("teamLocationCreated"),
        createFailed: t("createFailed"),
        change: t("change"),
        delete: t("delete"),
        changeTitle: t("changeTitle"),
        changeDescription: t("changeDescription"),
        itemUpdated: t("teamLocationUpdated"),
        updateFailed: t("updateFailed"),
        deleteConfirmTitle: t("deleteConfirmTitle"),
        deleteConfirmDescription: (name) => t("deleteConfirmDescription", { name }),
        itemDeleted: t("teamLocationDeleted"),
        deleteFailed: t("deleteFailed"),
        cancel: tCommon("cancel"),
      }}
    />
  );
}
