// TagScan's "TagManagement" screen: a table of registered RFID tags with
// add/change/delete — see TagManagement for the actual UI.

import { getTranslations } from "next-intl/server";
import { ServerApiError, serverApiFetch } from "@/lib/server-api";
import type { Product, RfidTag, TagscanKarOption } from "@/lib/types";
import { TagManagement } from "@/components/module-1/tag-management";

export default async function TagscanTagManagementPage() {
  const tErrors = await getTranslations("errors");

  let tags: RfidTag[] | null = null;
  let products: Product[] = [];
  let kars: TagscanKarOption[] = [];
  try {
    tags = await serverApiFetch<RfidTag[]>("/api/modules/module-1/tags");
    // Powers the "Assigned Product" dropdown on the create/edit form —
    // fetched separately since a user might be able to manage tags
    // without also being able to view the Products screen directly.
    products = await serverApiFetch<Product[]>("/api/modules/module-9/products").catch(() => []);
    // Powers the "Karnummer" dropdown — every kar of KarTracker's
    // KarManagement, served by TagScan itself (no KarTracker rights needed).
    kars = await serverApiFetch<TagscanKarOption[]>("/api/modules/module-1/kars").catch(() => []);
  } catch (error) {
    if (error instanceof ServerApiError && error.status === 403) {
      return <p className="text-sm text-destructive">{tErrors("forbidden")}</p>;
    }
    throw error;
  }

  return <TagManagement initialTags={tags} products={products} kars={kars} />;
}
