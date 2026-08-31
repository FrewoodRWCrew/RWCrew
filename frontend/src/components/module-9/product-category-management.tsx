"use client";

// MasterData's "Categorie" screen: a thin wrapper around the shared
// LookupManagement component (see lookup-management.tsx), supplying its
// own translated labels and api.ts functions — one of the four lookup
// lists ("selection criteria") nested under Products, alongside Type,
// Magazijn, and Limiet.

import { useTranslations } from "next-intl";
import { createProductCategory, deleteProductCategory, updateProductCategory } from "@/lib/api";
import type { ProductCategory } from "@/lib/types";
import { LookupManagement } from "@/components/module-9/lookup-management";

interface ProductCategoryManagementProps {
  initialProductCategories: ProductCategory[];
}

export function ProductCategoryManagement({ initialProductCategories }: ProductCategoryManagementProps) {
  const t = useTranslations("masterdata.productCategories");
  const tCommon = useTranslations("common");

  return (
    <LookupManagement
      initialItems={initialProductCategories}
      create={createProductCategory}
      update={updateProductCategory}
      remove={deleteProductCategory}
      labels={{
        title: t("title"),
        description: t("description"),
        tableName: t("tableName"),
        tableActions: t("tableActions"),
        newItem: t("newProductCategory"),
        nameLabel: t("nameLabel"),
        createTitle: t("createTitle"),
        createDescription: t("createDescription"),
        itemCreated: t("productCategoryCreated"),
        createFailed: t("createFailed"),
        change: t("change"),
        delete: t("delete"),
        changeTitle: t("changeTitle"),
        changeDescription: t("changeDescription"),
        itemUpdated: t("productCategoryUpdated"),
        updateFailed: t("updateFailed"),
        deleteConfirmTitle: t("deleteConfirmTitle"),
        deleteConfirmDescription: (name) => t("deleteConfirmDescription", { name }),
        itemDeleted: t("productCategoryDeleted"),
        deleteFailed: t("deleteFailed"),
        cancel: tCommon("cancel"),
      }}
    />
  );
}
