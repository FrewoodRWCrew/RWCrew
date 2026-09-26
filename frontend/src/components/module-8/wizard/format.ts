// Small display helpers shared by the Ploeg Wizard and the Ploegfiche.

/** "dd-mm-yyyy" from an ISO date or date-time string — the app's
 *  established fixed date format (same as the PDFs). */
export function formatDate(value: string): string {
  const [year, month, day] = value.slice(0, 10).split("-");
  return `${day}-${month}-${year}`;
}

/** A festival's period: one date for a one-day festival, else a range. */
export function formatFestivalPeriod(startDate: string, endDate: string): string {
  return startDate === endDate ? formatDate(startDate) : `${formatDate(startDate)} – ${formatDate(endDate)}`;
}

/** "Name — description" label for a delivery location. */
export function locationLabel(location: { name: string; description: string | null }): string {
  return location.description ? `${location.name} — ${location.description}` : location.name;
}
