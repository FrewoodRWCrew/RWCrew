// KarTracker's "KarManagement" screen: the fleet registry itself — see
// KarManagement for the actual UI.

import { getTranslations } from "next-intl/server";
import { ServerApiError, serverApiFetch } from "@/lib/server-api";
import type { KarTrackerKar, KarTrackerKarStatus, Product, Team } from "@/lib/types";
import { KarManagement } from "@/components/module-2/kar-management";

export default async function KarManagementPage() {
  const tErrors = await getTranslations("errors");

  let karren: KarTrackerKar[] | null = null;
  let karStatuses: KarTrackerKarStatus[] = [];
  let products: Product[] = [];
  let teams: Team[] = [];
  try {
    // These four are independent of each other, so fetch them
    // concurrently instead of one after another. The status/product/team
    // lookups are caught separately: a user might manage karren without
    // also being able to view the KarStatussen screen or module-9's
    // Products/Teams directly, in which case their dropdown just starts empty.
    [karren, karStatuses, products, teams] = await Promise.all([
      serverApiFetch<KarTrackerKar[]>("/api/modules/module-2/karren"),
      serverApiFetch<KarTrackerKarStatus[]>("/api/modules/module-2/kar-statuses").catch(() => []),
      serverApiFetch<Product[]>("/api/modules/module-9/products").catch(() => []),
      // Powers the "Ploeg" (Team) dropdown, sourced from module-9's
      // existing Teams master data.
      serverApiFetch<Team[]>("/api/modules/module-9/teams").catch(() => []),
    ]);
  } catch (error) {
    if (error instanceof ServerApiError && error.status === 403) {
      return <p className="text-sm text-destructive">{tErrors("forbidden")}</p>;
    }
    throw error;
  }

  return <KarManagement initialKarren={karren} karStatuses={karStatuses} products={products} teams={teams} />;
}
