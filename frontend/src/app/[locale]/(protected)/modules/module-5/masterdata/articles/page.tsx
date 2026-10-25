// Atelier's "Masterdata > Artikelen" screen — see ArticleManagement.

import { getTranslations } from "next-intl/server";
import { serverApiFetch } from "@/lib/server-api";
import type { AtelierArticle, AtelierSize } from "@/lib/types";
import { ArticleManagement } from "@/components/module-5/article-management";
import { atelierCan, loadAtelierPage } from "@/components/module-5/atelier-page-data";

export default async function AtelierArticlesPage() {
  const data = await loadAtelierPage("articles");
  if (!data) {
    const tErrors = await getTranslations("errors");
    return <p className="text-sm text-destructive">{tErrors("forbidden")}</p>;
  }

  const [articles, sizes] = await Promise.all([
    serverApiFetch<AtelierArticle[]>("/api/modules/module-5/articles"),
    serverApiFetch<AtelierSize[]>("/api/modules/module-5/sizes"),
  ]);
  return (
    <ArticleManagement
      initialArticles={articles}
      sizes={sizes}
      canCreate={atelierCan(data.permissions, "articles", "create")}
      canEdit={atelierCan(data.permissions, "articles", "edit")}
      canDelete={atelierCan(data.permissions, "articles", "delete")}
    />
  );
}
