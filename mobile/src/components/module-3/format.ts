// Formatting helpers for the Intervention Requests screens.

import type { Language } from "../../i18n";
import type { InterventionRequest, Lookups } from "../../lib/types";

// "24/09/2026 14:30" (Dutch/Belgian order) or "24/09/2026, 14:30" (English).
export function formatDateTime(iso: string | null | undefined, language: Language): string {
  if (!iso) return "";
  return new Date(iso).toLocaleString(language === "nl" ? "nl-BE" : "en-GB", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

// A request's "Ploeg": the MasterData team's name when it points to one,
// otherwise the free text a customer typed.
export function teamLabel(request: InterventionRequest, lookups: Lookups | null): string {
  if (request.team_id !== null) {
    return lookups?.teams.find((team) => team.id === request.team_id)?.name ?? "";
  }
  return request.team_name ?? "";
}
