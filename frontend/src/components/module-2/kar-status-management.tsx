"use client";

// KarTracker's "KarStatussen" screen: a thin wrapper around the shared
// LookupManagement component (see components/module-9/lookup-management.tsx),
// supplying its own translated labels and api.ts functions — same pattern
// as MasterData's SeasonManagement.

import { useTranslations } from "next-intl";
import { createKarStatus, deleteKarStatus, updateKarStatus } from "@/lib/api";
import type { KarTrackerKarStatus } from "@/lib/types";
import { LookupManagement } from "@/components/module-9/lookup-management";

interface KarStatusManagementProps {
  initialKarStatuses: KarTrackerKarStatus[];
}

export function KarStatusManagement({ initialKarStatuses }: KarStatusManagementProps) {
  const t = useTranslations("karTracker.karStatuses");
  const tCommon = useTranslations("common");

  return (
    <LookupManagement
      initialItems={initialKarStatuses}
      create={createKarStatus}
      update={updateKarStatus}
      remove={deleteKarStatus}
      labels={{
        title: t("title"),
        description: t("description"),
        tableName: t("tableName"),
        tableActions: t("tableActions"),
        newItem: t("newKarStatus"),
        nameLabel: t("nameLabel"),
        createTitle: t("createTitle"),
        createDescription: t("createDescription"),
        itemCreated: t("karStatusCreated"),
        createFailed: t("createFailed"),
        change: t("change"),
        delete: t("delete"),
        changeTitle: t("changeTitle"),
        changeDescription: t("changeDescription"),
        itemUpdated: t("karStatusUpdated"),
        updateFailed: t("updateFailed"),
        deleteConfirmTitle: t("deleteConfirmTitle"),
        deleteConfirmDescription: (name) => t("deleteConfirmDescription", { name }),
        itemDeleted: t("karStatusDeleted"),
        deleteFailed: t("deleteFailed"),
        cancel: tCommon("cancel"),
      }}
    />
  );
}
