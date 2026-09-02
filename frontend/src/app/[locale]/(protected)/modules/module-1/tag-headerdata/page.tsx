// TagScan's "Tag Headerdata" screen: scan the "Unreaded Tags" intake
// folder and show every CSV file logged so far — see TagHeaderData for
// the actual UI.

import { getTranslations } from "next-intl/server";
import { ServerApiError, serverApiFetch } from "@/lib/server-api";
import type { TagHeaderDataEntry } from "@/lib/types";
import { TagHeaderData } from "@/components/module-1/tag-headerdata";

export default async function TagscanTagHeaderDataPage() {
  const tErrors = await getTranslations("errors");

  let entries: TagHeaderDataEntry[] | null = null;
  try {
    entries = await serverApiFetch<TagHeaderDataEntry[]>("/api/modules/module-1/header-data");
  } catch (error) {
    if (error instanceof ServerApiError && error.status === 403) {
      return <p className="text-sm text-destructive">{tErrors("forbidden")}</p>;
    }
    throw error;
  }

  return <TagHeaderData initialEntries={entries} />;
}
