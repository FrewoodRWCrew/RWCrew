"use client";

// StockMaster's "Kar laden" page shows one of two screens:
// - the loading overview of every kar (kar-load-overview.tsx), by default;
// - the booking panel for one kar (booking-panel.tsx), once a kar was
//   opened with "Laden" (?kar=<id>), or when arriving from another screen
//   with a kar, a product or a source kar in the URL (?kar=, ?product=, ?from=).

import { useSearchParams } from "next/navigation";
import type { Season, StockMasterMyPermissions } from "@/lib/types";
import { BookingPanel } from "@/components/module-4/booking-panel";
import { KarLoadOverview } from "@/components/module-4/kar-load-overview";

interface KarLoadScreenProps {
  seasons: Season[];
  permissions: StockMasterMyPermissions;
}

export function KarLoadScreen({ seasons, permissions }: KarLoadScreenProps) {
  const searchParams = useSearchParams();
  const opensBooking = ["kar", "product", "from"].some((key) => searchParams.has(key));

  return opensBooking ? (
    // Keyed on the kar, so opening another kar starts with a fresh basket.
    <BookingPanel key={searchParams.get("kar") ?? "none"} action="kar_load" seasons={seasons} permissions={permissions} />
  ) : (
    <KarLoadOverview seasons={seasons} permissions={permissions} />
  );
}
