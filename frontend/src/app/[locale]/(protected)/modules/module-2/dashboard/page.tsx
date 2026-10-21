// KarTracker's KPI dashboard ("KPI Overview") — the fleet, recent kar
// movements and the Plan a kar progress for the season picked in the header.
// It has its own URL because the module root opens on Kar Planning (see
// ../page.tsx). Access is already gated by the module's layout.tsx (a 403
// there shows the forbidden message before this ever renders); the
// dashboard endpoint itself is gated by plain module access too. The
// figures are loaded client-side because they follow the header's season,
// which only the browser knows.

import { KarTrackerDashboard } from "@/components/module-2/kartracker-dashboard";

export default function KarTrackerDashboardPage() {
  return <KarTrackerDashboard />;
}
