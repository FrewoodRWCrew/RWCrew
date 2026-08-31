"use client";

// MasterData's "Type" screen: a thin wrapper around the shared
// LookupManagement component (see lookup-management.tsx), supplying its
// own translated labels and api.ts functions — one of the four lookup
// lists ("selection criteria") nested under Products, alongside
// Magazijn, Categorie, and Limiet.

import { useTranslations } from "next-intl";
import { createProductType, deleteProductType, updateProductType } from "@/lib/api";
import type { ProductType } from "@/lib/types";
import { LookupManagement } from "@/components/module-9/lookup-management";

interface ProductTypeManagementProps {
  initialProductTypes: ProductType[];
}

export function ProductTypeManagement({ initialProductTypes }: ProductTypeManagementProps) {
  const t = useTranslations("masterdata.productTypes");
  const tCommon = useTranslations("common");

  return (
    <LookupManagement
      initialItems={initialProductTypes}
      create={createProductType}
      update={updateProductType}
      remove={deleteProductType}
      labels={{
        title: t("title"),
        description: t("description"),
        tableName: t("tableName"),
        tableActions: t("tableActions"),
        newItem: t("newProductType"),
        nameLabel: t("nameLabel"),
        createTitle: t("createTitle"),
        createDescription: t("createDescription"),
        itemCreated: t("productTypeCreated"),
        createFailed: t("createFailed"),
        change: t("change"),
        delete: t("delete"),
        changeTitle: t("changeTitle"),
        changeDescription: t("changeDescription"),
        itemUpdated: t("productTypeUpdated"),
        updateFailed: t("updateFailed"),
        deleteConfirmTitle: t("deleteConfirmTitle"),
        deleteConfirmDescription: (name) => t("deleteConfirmDescription", { name }),
        itemDeleted: t("productTypeDeleted"),
        deleteFailed: t("deleteFailed"),
        cancel: tCommon("cancel"),
      }}
    />
  );
}
