// A soft pill colour per kar status, for screens that show a kar's status as
// a badge (Kar Planning). Statuses have no colour of their own in the data,
// so one is picked from a fixed palette by a small hash of the status name:
// the same status always gets the same colour, on every screen and reload.

// Soft pill classes in the same style as module-theme.ts's badgeClassName.
const STATUS_PALETTE = [
  "bg-sky-100 text-sky-700 dark:bg-sky-500/15 dark:text-sky-300",
  "bg-emerald-100 text-emerald-700 dark:bg-emerald-500/15 dark:text-emerald-300",
  "bg-amber-100 text-amber-800 dark:bg-amber-500/15 dark:text-amber-300",
  "bg-rose-100 text-rose-700 dark:bg-rose-500/15 dark:text-rose-300",
  "bg-violet-100 text-violet-700 dark:bg-violet-500/15 dark:text-violet-300",
  "bg-teal-100 text-teal-700 dark:bg-teal-500/15 dark:text-teal-300",
  "bg-orange-100 text-orange-700 dark:bg-orange-500/15 dark:text-orange-300",
  "bg-slate-200 text-slate-700 dark:bg-slate-500/20 dark:text-slate-300",
];

/** The pill classes for one status name (case and surrounding spaces ignored). */
export function statusPillClassName(statusName: string): string {
  // A simple string hash (djb2), stable across browsers.
  let hash = 5381;
  for (const char of statusName.trim().toLowerCase()) {
    hash = (hash * 33 + char.charCodeAt(0)) >>> 0;
  }
  return STATUS_PALETTE[hash % STATUS_PALETTE.length];
}
