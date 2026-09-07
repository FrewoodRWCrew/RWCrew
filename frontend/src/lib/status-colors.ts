// The fixed palette an Intervention Status can be coloured with (see
// intervention-status-management.tsx), used to colour every row of the
// Intervention Requests list belonging to that status (see
// intervention-requests-management.tsx). Kept in sync by hand with the
// backend's StatusColor Literal in
// backend/app/schemas/intervention_requests.py — same idea as
// module-theme.ts's per-module colours, just for statuses instead of
// modules. Display names live in translations (interventionRequests.status
// .colorNames), not here — this file only carries the CSS classes.

export const STATUS_COLOR_KEYS = [
  "red",
  "orange",
  "amber",
  "green",
  "teal",
  "blue",
  "indigo",
  "purple",
  "gray",
] as const;

export type StatusColorKey = (typeof STATUS_COLOR_KEYS)[number];

interface StatusColorInfo {
  /** Applied to a request row whose status has this colour, so the whole
   *  line's text reads in this colour (see the tr[data-status-color] rule
   *  in globals.css that lets this win over each cell's own text colour). */
  textClassName: string;
  /** A small solid dot shown next to this colour's name in the picker. */
  swatchClassName: string;
}

export const STATUS_COLOR_INFO: Record<StatusColorKey, StatusColorInfo> = {
  red: { textClassName: "text-red-600 dark:text-red-400", swatchClassName: "bg-red-600" },
  orange: { textClassName: "text-orange-600 dark:text-orange-400", swatchClassName: "bg-orange-600" },
  amber: { textClassName: "text-amber-600 dark:text-amber-400", swatchClassName: "bg-amber-600" },
  green: { textClassName: "text-green-600 dark:text-green-400", swatchClassName: "bg-green-600" },
  teal: { textClassName: "text-teal-600 dark:text-teal-400", swatchClassName: "bg-teal-600" },
  blue: { textClassName: "text-blue-600 dark:text-blue-400", swatchClassName: "bg-blue-600" },
  indigo: { textClassName: "text-indigo-600 dark:text-indigo-400", swatchClassName: "bg-indigo-600" },
  purple: { textClassName: "text-purple-600 dark:text-purple-400", swatchClassName: "bg-purple-600" },
  gray: { textClassName: "text-gray-600 dark:text-gray-400", swatchClassName: "bg-gray-600" },
};

/** Whether a string is one of the known palette keys — used to safely
 *  index STATUS_COLOR_INFO with a value that came from the API as a plain
 *  string. */
export function isStatusColorKey(value: string): value is StatusColorKey {
  return (STATUS_COLOR_KEYS as readonly string[]).includes(value);
}

/** The same 9 colours as STATUS_COLOR_INFO, as raw hex (Tailwind's own
 *  600/400 shades) for use as a recharts `theme` fill — CSS classes can't
 *  be read back out as a fill color, so the KPI dashboard's status donut
 *  chart (see intervention-requests-dashboard.tsx) needs this instead of
 *  the Tailwind classes above. Keep both objects in sync by hand if a new
 *  status colour is ever added. */
export const STATUS_COLOR_CHART_HEX: Record<StatusColorKey, { light: string; dark: string }> = {
  red: { light: "#dc2626", dark: "#f87171" },
  orange: { light: "#ea580c", dark: "#fb923c" },
  amber: { light: "#d97706", dark: "#fbbf24" },
  green: { light: "#16a34a", dark: "#4ade80" },
  teal: { light: "#0d9488", dark: "#2dd4bf" },
  blue: { light: "#2563eb", dark: "#60a5fa" },
  indigo: { light: "#4f46e5", dark: "#818cf8" },
  purple: { light: "#9333ea", dark: "#c084fc" },
  gray: { light: "#4b5563", dark: "#9ca3af" },
};
