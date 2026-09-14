"use client";

// KarTracker's "Zone" screen: a thin wrapper around the shared
// LookupManagement component (see components/module-9/lookup-management.tsx),
// supplying its own translated labels and api.ts functions — same pattern
// as KarStatusManagement/MasterData's SeasonManagement.

import { useTranslations } from "next-intl";
import { createZone, deleteZone, updateZone } from "@/lib/api";
import type { KarTrackerZone } from "@/lib/types";
import { LookupManagement } from "@/components/module-9/lookup-management";

interface ZoneManagementProps {
  initialZones: KarTrackerZone[];
}

export function ZoneManagement({ initialZones }: ZoneManagementProps) {
  const t = useTranslations("karTracker.zones");
  const tCommon = useTranslations("common");

  return (
    <LookupManagement
      initialItems={initialZones}
      create={createZone}
      update={updateZone}
      remove={deleteZone}
      labels={{
        title: t("title"),
        description: t("description"),
        tableName: t("tableName"),
        tableActions: t("tableActions"),
        newItem: t("newZone"),
        nameLabel: t("nameLabel"),
        createTitle: t("createTitle"),
        createDescription: t("createDescription"),
        itemCreated: t("zoneCreated"),
        createFailed: t("createFailed"),
        change: t("change"),
        delete: t("delete"),
        changeTitle: t("changeTitle"),
        changeDescription: t("changeDescription"),
        itemUpdated: t("zoneUpdated"),
        updateFailed: t("updateFailed"),
        deleteConfirmTitle: t("deleteConfirmTitle"),
        deleteConfirmDescription: (name) => t("deleteConfirmDescription", { name }),
        itemDeleted: t("zoneDeleted"),
        deleteFailed: t("deleteFailed"),
        cancel: tCommon("cancel"),
      }}
    />
  );
}
