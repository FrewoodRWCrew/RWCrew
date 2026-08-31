"use client";

// MasterData's "Limiet" screen: a thin wrapper around the shared
// LookupManagement component (see lookup-management.tsx), supplying its
// own translated labels and api.ts functions — one of the four lookup
// lists ("selection criteria") nested under Products, alongside Type,
// Magazijn, and Categorie.

import { useTranslations } from "next-intl";
import { createProductLimit, deleteProductLimit, updateProductLimit } from "@/lib/api";
import type { ProductLimit } from "@/lib/types";
import { LookupManagement } from "@/components/module-9/lookup-management";

interface ProductLimitManagementProps {
  initialProductLimits: ProductLimit[];
}

export function ProductLimitManagement({ initialProductLimits }: ProductLimitManagementProps) {
  const t = useTranslations("masterdata.productLimits");
  const tCommon = useTranslations("common");

  return (
    <LookupManagement
      initialItems={initialProductLimits}
      create={createProductLimit}
      update={updateProductLimit}
      remove={deleteProductLimit}
      labels={{
        title: t("title"),
        description: t("description"),
        tableName: t("tableName"),
        tableActions: t("tableActions"),
        newItem: t("newProductLimit"),
        nameLabel: t("nameLabel"),
        createTitle: t("createTitle"),
        createDescription: t("createDescription"),
        itemCreated: t("productLimitCreated"),
        createFailed: t("createFailed"),
        change: t("change"),
        delete: t("delete"),
        changeTitle: t("changeTitle"),
        changeDescription: t("changeDescription"),
        itemUpdated: t("productLimitUpdated"),
        updateFailed: t("updateFailed"),
        deleteConfirmTitle: t("deleteConfirmTitle"),
        deleteConfirmDescription: (name) => t("deleteConfirmDescription", { name }),
        itemDeleted: t("productLimitDeleted"),
        deleteFailed: t("deleteFailed"),
        cancel: tCommon("cancel"),
      }}
    />
  );
}
