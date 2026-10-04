// KarTracker's landing page: the KPI dashboard ("KPI Overview") — the fleet,
// recent kar movements and the Plan a kar progress for the season picked in
// the header. Access is already gated by this route's own layout.tsx (a 403
// there shows the forbidden message before this ever renders); the
// dashboard endpoint itself is gated by plain module access too. The
// figures are loaded client-side because they follow the header's season,
// which only the browser knows.

import { KarTrackerDashboard } from "@/components/module-2/kartracker-dashboard";

export default function KarTrackerLandingPage() {
  return <KarTrackerDashboard />;
}
