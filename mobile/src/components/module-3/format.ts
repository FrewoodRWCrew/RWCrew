// Formatting helpers for the Intervention Requests screens.

import type { Language } from "../../i18n";
import type { InterventionRequest, Lookups } from "../../lib/types";

// "24/09/2026 14:30" (Dutch/Belgian order) or "24/09/2026, 14:30" (English).
// For real server timestamps (e.g. submitted_at), shown in the phone's timezone.
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

// ---- "Voorkeur levering" is a wall-clock time, not a real timestamp ----
// The web sends its <input type="datetime-local"> value as-is (e.g.
// "2026-09-07T23:39", no timezone), the backend stores those digits as if
// they were UTC, and the web shows them by slicing the string. So the digits
// in the ISO string ARE the time the user meant. The phone must read and
// write them the same way — never convert to/from the phone's timezone, or
// 23:39 on the web turns into 01:39 the next day on the phone.

const pad = (value: number) => String(value).padStart(2, "0");

// "2026-09-07T23:39" — the digits as typed; sorts correctly as plain text.
export function wallClockKey(iso: string): string {
  return iso.slice(0, 16);
}

// A phone-local Date holding exactly those digits (for the date picker and
// for working out the weekday).
export function parseWallClock(iso: string): Date {
  const [datePart, timePart = "00:00"] = wallClockKey(iso).split("T");
  const [year, month, day] = datePart.split("-").map(Number);
  const [hours, minutes] = timePart.split(":").map(Number);
  return new Date(year, month - 1, day, hours, minutes);
}

// The other direction: what the user picked on the phone, as the same
// timezone-less "2026-09-07T23:39:00" shape the web sends.
export function toWallClockIso(date: Date): string {
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}:00`;
}

// Weekday names, indexed like Date.getDay() (0 = Sunday).
const WEEKDAYS: Record<Language, string[]> = {
  nl: ["Zondag", "Maandag", "Dinsdag", "Woensdag", "Donderdag", "Vrijdag", "Zaterdag"],
  en: ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"],
};

// "Maandag 02/07/2026" / "Monday 02/07/2026" — date only. Built by hand
// instead of toLocaleDateString({ weekday }) so the result is identical on
// iOS and Android (Hermes' Intl support differs).
export function formatDeliveryDate(iso: string | null | undefined, language: Language): string {
  if (!iso) return "";
  const date = parseWallClock(iso);
  return `${WEEKDAYS[language][date.getDay()]} ${pad(date.getDate())}/${pad(date.getMonth() + 1)}/${date.getFullYear()}`;
}

// "14:30" — time only (24-hour).
export function formatTime(iso: string | null | undefined): string {
  if (!iso) return "";
  return wallClockKey(iso).slice(11, 16);
}

// "07/09/2026 23:39" — date + time, for the form's date field.
export function formatWallClockDateTime(iso: string | null | undefined): string {
  if (!iso) return "";
  const date = parseWallClock(iso);
  return `${pad(date.getDate())}/${pad(date.getMonth() + 1)}/${date.getFullYear()} ${formatTime(iso)}`;
}

// A request's "Ploeg": the MasterData team's name when it points to one,
// otherwise the free text a customer typed.
export function teamLabel(request: InterventionRequest, lookups: Lookups | null): string {
  if (request.team_id !== null) {
    return lookups?.teams.find((team) => team.id === request.team_id)?.name ?? "";
  }
  return request.team_name ?? "";
}
