"use client";

// KarTracker's "Plan a kar" page shows one of two screens:
// - the planning overview of every kar (plan-kar-overview.tsx), by default;
// - the festival → afleverlocatie matrix of one team (plan-kar.tsx), once a
//   kar was opened with "Plannen" (?team=<id>).

import { useSearchParams } from "next/navigation";
import type {
  KarTrackerGroundplan,
  KarTrackerPlanKarAfleverlocatieOption,
  KarTrackerPlanKarOption,
} from "@/lib/types";
import { PlanKar } from "@/components/module-2/plan-kar";
import { PlanKarOverview } from "@/components/module-2/plan-kar-overview";

interface PlanKarScreenProps {
  teams: KarTrackerPlanKarOption[];
  afleverlocaties: KarTrackerPlanKarAfleverlocatieOption[];
  groundplans: KarTrackerGroundplan[];
}

export function PlanKarScreen({ teams, afleverlocaties, groundplans }: PlanKarScreenProps) {
  const searchParams = useSearchParams();
  const teamId = Number(searchParams.get("team"));

  return Number.isInteger(teamId) && teamId > 0 ? (
    // Keyed on the team, so opening another team starts from its saved plan.
    <PlanKar key={teamId} teamId={teamId} teams={teams} afleverlocaties={afleverlocaties} groundplans={groundplans} />
  ) : (
    <PlanKarOverview />
  );
}
