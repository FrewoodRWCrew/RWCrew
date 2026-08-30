// TagScan's "Dashboard" screen: a read-only, Explorer-style browser over
// the folder currently receiving incoming CSV scan files — see
// FileBrowser for the actual UI. Parsing/importing that data into the
// database is a later step; this one is purely for looking at what has
// arrived so far.

import { getTranslations } from "next-intl/server";
import { ServerApiError, serverApiFetch } from "@/lib/server-api";
import type { TagscanFileEntry, TagscanFolderNode } from "@/lib/types";
import { FileBrowser } from "@/components/module-1/file-browser";

interface DashboardPageData {
  tree: TagscanFolderNode;
  rootFiles: TagscanFileEntry[];
}

export default async function TagscanDashboardPage() {
  const tErrors = await getTranslations("errors");

  let data: DashboardPageData | null = null;
  try {
    const tree = await serverApiFetch<TagscanFolderNode>("/api/modules/module-1/files/tree");
    const rootFiles = await serverApiFetch<TagscanFileEntry[]>(
      `/api/modules/module-1/files?path=${encodeURIComponent(tree.path)}`,
    );
    data = { tree, rootFiles };
  } catch (error) {
    if (error instanceof ServerApiError && error.status === 403) {
      return <p className="text-sm text-destructive">{tErrors("forbidden")}</p>;
    }
    throw error;
  }

  return <FileBrowser initialTree={data.tree} initialFiles={data.rootFiles} />;
}
