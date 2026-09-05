"use client";

// MasterData's "Delivery Method" screen (nested under "Teams"): a thin
// wrapper around the shared LookupManagement component (see
// lookup-management.tsx), supplying its own translated labels and
// api.ts functions, plus `field="delivery_method"` since this screen's
// value isn't called "name" like the original five lookup screens.

import { useTranslations } from "next-intl";
import { createDeliveryMethod, deleteDeliveryMethod, updateDeliveryMethod } from "@/lib/api";
import type { DeliveryMethod } from "@/lib/types";
import { LookupManagement } from "@/components/module-9/lookup-management";

interface DeliveryMethodManagementProps {
  initialDeliveryMethods: DeliveryMethod[];
}

export function DeliveryMethodManagement({ initialDeliveryMethods }: DeliveryMethodManagementProps) {
  const t = useTranslations("masterdata.deliveryMethod");
  const tCommon = useTranslations("common");

  return (
    <LookupManagement
      field="delivery_method"
      initialItems={initialDeliveryMethods}
      create={createDeliveryMethod}
      update={updateDeliveryMethod}
      remove={deleteDeliveryMethod}
      labels={{
        title: t("title"),
        description: t("description"),
        tableName: t("tableName"),
        tableActions: t("tableActions"),
        newItem: t("newDeliveryMethod"),
        nameLabel: t("deliveryMethodLabel"),
        createTitle: t("createTitle"),
        createDescription: t("createDescription"),
        itemCreated: t("deliveryMethodCreated"),
        createFailed: t("createFailed"),
        change: t("change"),
        delete: t("delete"),
        changeTitle: t("changeTitle"),
        changeDescription: t("changeDescription"),
        itemUpdated: t("deliveryMethodUpdated"),
        updateFailed: t("updateFailed"),
        deleteConfirmTitle: t("deleteConfirmTitle"),
        deleteConfirmDescription: (name) => t("deleteConfirmDescription", { name }),
        itemDeleted: t("deliveryMethodDeleted"),
        deleteFailed: t("deleteFailed"),
        cancel: tCommon("cancel"),
      }}
    />
  );
}
