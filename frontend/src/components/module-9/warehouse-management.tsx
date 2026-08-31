"use client";

// MasterData's "Magazijn" screen: a thin wrapper around the shared
// LookupManagement component (see lookup-management.tsx), supplying its
// own translated labels and api.ts functions — one of the four lookup
// lists ("selection criteria") nested under Products, alongside Type,
// Categorie, and Limiet.

import { useTranslations } from "next-intl";
import { createWarehouse, deleteWarehouse, updateWarehouse } from "@/lib/api";
import type { Warehouse } from "@/lib/types";
import { LookupManagement } from "@/components/module-9/lookup-management";

interface WarehouseManagementProps {
  initialWarehouses: Warehouse[];
}

export function WarehouseManagement({ initialWarehouses }: WarehouseManagementProps) {
  const t = useTranslations("masterdata.warehouses");
  const tCommon = useTranslations("common");

  return (
    <LookupManagement
      initialItems={initialWarehouses}
      create={createWarehouse}
      update={updateWarehouse}
      remove={deleteWarehouse}
      labels={{
        title: t("title"),
        description: t("description"),
        tableName: t("tableName"),
        tableActions: t("tableActions"),
        newItem: t("newWarehouse"),
        nameLabel: t("nameLabel"),
        createTitle: t("createTitle"),
        createDescription: t("createDescription"),
        itemCreated: t("warehouseCreated"),
        createFailed: t("createFailed"),
        change: t("change"),
        delete: t("delete"),
        changeTitle: t("changeTitle"),
        changeDescription: t("changeDescription"),
        itemUpdated: t("warehouseUpdated"),
        updateFailed: t("updateFailed"),
        deleteConfirmTitle: t("deleteConfirmTitle"),
        deleteConfirmDescription: (name) => t("deleteConfirmDescription", { name }),
        itemDeleted: t("warehouseDeleted"),
        deleteFailed: t("deleteFailed"),
        cancel: tCommon("cancel"),
      }}
    />
  );
}
