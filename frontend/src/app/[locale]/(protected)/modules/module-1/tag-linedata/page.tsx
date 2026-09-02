// TagScan's "Tag Linedata" screen: every CSV data line a scan has
// produced, enriched with a snapshot of its matched TagManagement tag —
// see TagLineData for the actual UI.

import { getTranslations } from "next-intl/server";
import { ServerApiError, serverApiFetch } from "@/lib/server-api";
import type { TagLineDataEntry } from "@/lib/types";
import { TagLineData } from "@/components/module-1/tag-linedata";

export default async function TagscanTagLineDataPage() {
  const tErrors = await getTranslations("errors");

  let entries: TagLineDataEntry[] | null = null;
  try {
    entries = await serverApiFetch<TagLineDataEntry[]>("/api/modules/module-1/line-data");
  } catch (error) {
    if (error instanceof ServerApiError && error.status === 403) {
      return <p className="text-sm text-destructive">{tErrors("forbidden")}</p>;
    }
    throw error;
  }

  return <TagLineData initialEntries={entries} />;
}
