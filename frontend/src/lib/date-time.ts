// Date/time display helpers for the whole app: every moment is shown in
// Belgian time (Europe/Brussels — winter and summer time handled
// automatically), whatever offset the backend's ISO string carries.
// A fixed time zone and a fixed output shape (built from formatToParts, not
// toLocaleString) keep server render and browser hydration identical.
//
// Plain dates without a time ("YYYY-MM-DD", e.g. festival days) have no time
// zone: these helpers leave them exactly as they are.

const BELGIAN_TIME_ZONE = "Europe/Brussels";

// One shared formatter giving the numeric parts of a moment in Belgian time.
const PARTS_FORMAT = new Intl.DateTimeFormat("en-GB", {
  timeZone: BELGIAN_TIME_ZONE,
  year: "numeric",
  month: "2-digit",
  day: "2-digit",
  hour: "2-digit",
  minute: "2-digit",
  hourCycle: "h23",
});

interface BelgianParts {
  year: string;
  month: string;
  day: string;
  hour: string;
  minute: string;
}

/** A value with only a date ("YYYY-MM-DD") — never shifted by a time zone. */
function isDateOnly(value: string): boolean {
  return /^\d{4}-\d{2}-\d{2}$/.test(value);
}

/** The year/month/day/hour/minute of an ISO moment in Belgian time, or null
 * when the value can't be parsed. */
function belgianParts(isoValue: string): BelgianParts | null {
  if (isDateOnly(isoValue)) {
    const [year, month, day] = isoValue.split("-");
    return { year, month, day, hour: "00", minute: "00" };
  }
  // No offset (e.g. a value just typed into a datetime-local input): it is
  // already Belgian wall-clock time, so read it as-is instead of letting the
  // runtime's own time zone shift it.
  const wallClock = /^(\d{4})-(\d{2})-(\d{2})[T ](\d{2}):(\d{2})(:\d{2}(\.\d+)?)?$/.exec(isoValue);
  if (wallClock) {
    const [, year, month, day, hour, minute] = wallClock;
    return { year, month, day, hour, minute };
  }
  const moment = new Date(isoValue);
  if (Number.isNaN(moment.getTime())) return null;
  const parts: Record<string, string> = {};
  for (const part of PARTS_FORMAT.formatToParts(moment)) parts[part.type] = part.value;
  return { year: parts.year, month: parts.month, day: parts.day, hour: parts.hour, minute: parts.minute };
}

/** "YYYY-MM-DD HH:mm" in Belgian time ("" for an empty value). */
export function formatDateTime(isoValue: string | null | undefined): string {
  const parts = isoValue ? belgianParts(isoValue) : null;
  return parts ? `${parts.year}-${parts.month}-${parts.day} ${parts.hour}:${parts.minute}` : "";
}

/** "YYYY-MM-DD", the Belgian calendar date — also the key used to group
 * rows per day ("" for an empty value). */
export function formatDate(isoValue: string | null | undefined): string {
  const parts = isoValue ? belgianParts(isoValue) : null;
  return parts ? `${parts.year}-${parts.month}-${parts.day}` : "";
}

/** "dd-mm-yyyy", the Belgian calendar date in the app's PDF-style format. */
export function formatDateNl(isoValue: string | null | undefined): string {
  const parts = isoValue ? belgianParts(isoValue) : null;
  return parts ? `${parts.day}-${parts.month}-${parts.year}` : "";
}

/** "dd-mm-yyyy HH:mm" in Belgian time. */
export function formatDateTimeNl(isoValue: string | null | undefined): string {
  const parts = isoValue ? belgianParts(isoValue) : null;
  return parts ? `${parts.day}-${parts.month}-${parts.year} ${parts.hour}:${parts.minute}` : "";
}

/** "HH:mm" in Belgian time. */
export function formatTime(isoValue: string | null | undefined): string {
  const parts = isoValue ? belgianParts(isoValue) : null;
  return parts ? `${parts.hour}:${parts.minute}` : "";
}

/** "YYYY-MM-DDTHH:mm" in Belgian time: the value an
 * <input type="datetime-local"> needs. The form sends it back without a
 * time zone, and the backend reads that as Belgian time. */
export function toDateTimeLocalValue(isoValue: string | null | undefined): string {
  const parts = isoValue ? belgianParts(isoValue) : null;
  return parts ? `${parts.year}-${parts.month}-${parts.day}T${parts.hour}:${parts.minute}` : "";
}
