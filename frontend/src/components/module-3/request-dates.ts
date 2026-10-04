// Small date and status helpers for intervention requests, shared by the
// desktop requests screen (intervention-requests-management.tsx) and the
// phone's Akties list and request form (components/phone/module-3/).
// Every moment is shown in Belgian time via the app-wide helpers in
// lib/date-time.ts (re-exported here so existing imports keep working).

import type { InterventionStatus } from "@/lib/types";

export { formatDateTime, formatTime, toDateTimeLocalValue } from "@/lib/date-time";

// belgianDayKey: the Belgian calendar day ("YYYY-MM-DD") of a preferred
// delivery — the key requests are grouped by ("" when none is set).
export { formatDate as belgianDayKey } from "@/lib/date-time";

/** The status a brand-new request should default to, so staff don't have
 * to remember to set it themselves every time — matched by name against
 * the live statuses list (ids are generated, so can't be hardcoded).
 * Falls back to unselected if no status is literally named "Nieuw".
 */
export function defaultStatusId(statuses: InterventionStatus[]): number {
  return statuses.find((status) => status.name === "Nieuw")?.id ?? 0;
}

/** "dd-mm-yyyy", for a group's date subtitle — takes the date-only
 * "YYYY-MM-DD" slice already used as this table's grouping key, distinct
 * from formatDateTime's HH:mm-inclusive table-cell format.
 */
export function formatDateOnly(dateOnly: string): string {
  const [year, month, day] = dateOnly.split("-");
  return `${day}-${month}-${year}`;
}

/** Translation keys for interventionRequests.requests.weekdays, indexed
 * exactly like Date#getUTCDay() (0 = Sunday .. 6 = Saturday).
 */
export const WEEKDAY_KEYS = ["sunday", "monday", "tuesday", "wednesday", "thursday", "friday", "saturday"] as const;

/** Which weekday a "YYYY-MM-DD" date key falls on — parsed as UTC
 * midnight (not the runtime's local timezone) so it's the same on the
 * server and in the browser, same deterministic-parsing reasoning as
 * formatDateTime/formatDateOnly avoiding toLocaleString elsewhere in this
 * file.
 */
export function weekdayKeyFor(dateOnly: string): (typeof WEEKDAY_KEYS)[number] {
  return WEEKDAY_KEYS[new Date(`${dateOnly}T00:00:00Z`).getUTCDay()];
}
