// The processing status every scanned file (Tag Headerdata) and line (Tag
// Linedata) carries: whether its action (e.g. "Assignment" → create the tag)
// has been carried out — see backend app/modules/module_1/line_processing.py.
// One place for the values and their colours, so both screens and the
// waiting-actions dialog always look the same.

import type { TagProcessStatus } from "@/lib/types";

/** Every status, in the order the filter dropdowns list them. */
export const PROCESS_STATUS_VALUES: TagProcessStatus[] = ["new", "loaded", "cancelled"];

/** Whole-row text colour: orange = waiting, green = done, red = cancelled.
 * Dark-mode variants keep contrast against the dark default theme.
 */
export const PROCESS_STATUS_ROW_CLASS: Record<TagProcessStatus, string> = {
  new: "text-orange-600 dark:text-orange-400",
  loaded: "text-green-600 dark:text-green-400",
  cancelled: "text-red-600 dark:text-red-400",
};

/** Soft pill for the status cell itself, same colours as the row. */
export const PROCESS_STATUS_BADGE_CLASS: Record<TagProcessStatus, string> = {
  new: "border-orange-500/40 bg-orange-500/10 text-orange-700 dark:text-orange-300",
  loaded: "border-green-500/40 bg-green-500/10 text-green-700 dark:text-green-300",
  cancelled: "border-red-500/40 bg-red-500/10 text-red-700 dark:text-red-300",
};
