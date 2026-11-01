// The Scans module's "JSON source files" screen — see WristbandFileBrowser.
// Opens on the newest day. "delete" on this screen allows deleting files.

import { getTranslations } from "next-intl/server";
import { ServerApiError, serverApiFetch } from "@/lib/server-api";
import type { TagscanFileEntry, TagscanFolderNode, TagscanMyPermissions } from "@/lib/types";
import { WristbandFileBrowser } from "@/components/module-1/wristband-file-browser";

const BASE = "/api/modules/module-1/wristband";

export default async function WristbandFilesPage() {
  const tErrors = await getTranslations("errors");

  try {
    const tree = await serverApiFetch<TagscanFolderNode>(`${BASE}/files/tree`);
    // The day folders sort by date, so the last one is the newest.
    const initialFolderPath = tree.children[tree.children.length - 1]?.path ?? tree.path;
    const [initialFiles, permissions] = await Promise.all([
      serverApiFetch<TagscanFileEntry[]>(`${BASE}/files?path=${encodeURIComponent(initialFolderPath)}`),
      serverApiFetch<TagscanMyPermissions>("/api/modules/module-1/me/permissions"),
    ]);
    return (
      <WristbandFileBrowser
        initialTree={tree}
        initialFolderPath={initialFolderPath}
        initialFiles={initialFiles}
        canDelete={permissions.deletable_screen_keys.includes("tagscan.wristband-files")}
      />
    );
  } catch (error) {
    if (error instanceof ServerApiError && error.status === 403) {
      return <p className="text-sm text-destructive">{tErrors("forbidden")}</p>;
    }
    throw error;
  }
}
