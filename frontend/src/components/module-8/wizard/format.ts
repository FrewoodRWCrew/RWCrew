// Small display helpers shared by the Ploeg Wizard and the Ploegfiche.

import { formatDateNl } from "@/lib/date-time";

/** "dd-mm-yyyy" from an ISO date or date-time string — the app's
 *  established fixed date format (same as the PDFs). A date-time gives its
 *  Belgian calendar date; a plain date is shown as-is. */
export function formatDate(value: string): string {
  return formatDateNl(value);
}

/** A festival's period: one date for a one-day festival, else a range. */
export function formatFestivalPeriod(startDate: string, endDate: string): string {
  return startDate === endDate ? formatDate(startDate) : `${formatDate(startDate)} – ${formatDate(endDate)}`;
}

/** "Name — description" label for a delivery location. */
export function locationLabel(location: { name: string; description: string | null }): string {
  return location.description ? `${location.name} — ${location.description}` : location.name;
}
