// TagScan's "CSV Source Files" screen: a read-only, Explorer-style
// browser over the folder currently receiving incoming CSV scan files —
// see FileBrowser for the actual UI. Users with "delete" on this screen
// can also delete files from the server there. Moved here (off the module's root URL) once
// TagScan got its own landing page — see modules/module-1/page.tsx.

import { getTranslations } from "next-intl/server";
import { ServerApiError, serverApiFetch } from "@/lib/server-api";
import type { TagscanFileEntry, TagscanFolderNode, TagscanMyPermissions } from "@/lib/types";
import { FileBrowser } from "@/components/module-1/file-browser";

interface DashboardPageData {
  tree: TagscanFolderNode;
  initialFolderPath: string;
  initialFiles: TagscanFileEntry[];
  canDelete: boolean;
}

// The intake folder new CSVs land in (backend: UNREADED_SUBFOLDER) — the
// screen opens on it, since that's what people come here to look at.
const DEFAULT_FOLDER_NAME = "Unreaded Tags";

export default async function TagscanFilesPage() {
  const tErrors = await getTranslations("errors");

  let data: DashboardPageData | null = null;
  try {
    const tree = await serverApiFetch<TagscanFolderNode>("/api/modules/module-1/files/tree");
    // Open on "Unreaded Tags" (case-insensitive); fall back to the root
    // folder while that folder doesn't exist yet.
    const defaultFolder = tree.children.find(
      (child) => child.name.toLowerCase() === DEFAULT_FOLDER_NAME.toLowerCase(),
    );
    const initialFolderPath = defaultFolder?.path ?? tree.path;
    const initialFiles = await serverApiFetch<TagscanFileEntry[]>(
      `/api/modules/module-1/files?path=${encodeURIComponent(initialFolderPath)}`,
    );
    // Already fetched by the module layout — request memoization means no
    // second network call. "delete" on this screen allows deleting files.
    const permissions = await serverApiFetch<TagscanMyPermissions>("/api/modules/module-1/me/permissions");
    const canDelete = permissions.deletable_screen_keys.includes("tagscan.dashboard");
    data = { tree, initialFolderPath, initialFiles, canDelete };
  } catch (error) {
    if (error instanceof ServerApiError && error.status === 403) {
      return <p className="text-sm text-destructive">{tErrors("forbidden")}</p>;
    }
    throw error;
  }

  return (
    <FileBrowser
      initialTree={data.tree}
      initialFolderPath={data.initialFolderPath}
      initialFiles={data.initialFiles}
      canDelete={data.canDelete}
    />
  );
}
