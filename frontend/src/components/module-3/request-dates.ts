// Small date and status helpers for intervention requests, shared by the
// desktop requests screen (intervention-requests-management.tsx) and the
// phone's Akties list and request form (components/phone/module-3/).
// Dates arrive as ISO strings holding the wall-clock time; they are sliced,
// never converted, so server render, browser and phone all show the same.

import type { InterventionStatus } from "@/lib/types";

/** Plain string slicing instead of toLocaleString(): that depends on the
 * runtime's default locale/timezone, which differs between the server
 * (during SSR) and the browser (during hydration) — causing a hydration
 * mismatch. Slicing the already-ISO string is deterministic everywhere
 * (see tag-linedata.tsx's identical helper).
 */
export function formatDateTime(isoDateTime: string | null): string {
  return isoDateTime ? isoDateTime.slice(0, 16).replace("T", " ") : "";
}

/** "YYYY-MM-DDTHH:mm", the value shape <input type="datetime-local">
 * expects — just the first 16 characters of an ISO string.
 */
export function toDateTimeLocalValue(isoDateTime: string | null): string {
  return isoDateTime ? isoDateTime.slice(0, 16) : "";
}

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
