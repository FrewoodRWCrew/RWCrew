// Shared look of the Ploeg Wizard, so every step marks "what you chose" and
// "what still needs saving" the same way. The accent is the module's own
// colour: inside Altsien Select `--primary` is fuchsia (see
// lib/module-theme.ts moduleThemeStyle), so `primary` classes follow it.

import { cn } from "@/lib/utils";

/** One option/list row inside a step (a festival checkbox row, a person, a
 *  request, a table row): white with a border, the accent border on hover,
 *  and — once chosen/filled in — an accent border + soft accent background
 *  with a bold name, so the user sees at a glance what is selected.
 */
export function wizardRowClassName(selected: boolean) {
  return cn(
    "rounded-md border bg-card transition-colors hover:border-primary/60",
    selected && "border-primary bg-primary/10 font-semibold dark:bg-primary/15",
  );
}

/** A table row (e.g. step 2's festival rows): only the background marks a
 *  filled-in row, since table rows have no border of their own.
 */
export function wizardTableRowClassName(selected: boolean) {
  return cn("group", selected && "bg-primary/10 hover:bg-primary/15 dark:bg-primary/15");
}

/** The "you still have unsaved changes" note: an orange pill, so it isn't
 *  overlooked next to the Save button.
 */
export const wizardUnsavedClassName =
  "inline-flex w-fit items-center gap-1.5 rounded-full border border-orange-500/40 bg-orange-500/10 px-2.5 py-0.5 text-xs font-medium text-orange-700 dark:text-orange-300";
