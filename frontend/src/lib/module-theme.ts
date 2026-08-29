// Each of the 9 modules gets its own distinct accent colour, so tiles
// (and later, each module's own pages) are easy to tell apart at a
// glance. We reuse Tailwind's built-in colour scales — already tuned for
// good contrast — rather than inventing custom colours by hand.
//
// Once real module names/branding are decided, these colours (and their
// order) can simply be reassigned here without touching any component.

export interface ModuleTheme {
  /** Classes for the module's tile on the landing page: a solid background
   *  covering the whole tile, plus a text colour readable on top of it. */
  tileClassName: string;
  /** Classes for the softer, pill-shaped badge shown on the module's own
   *  page (see ModulePlaceholderPage) — a light tint rather than solid fill. */
  badgeClassName: string;
}

const MODULE_THEMES_BY_KEY: Record<string, ModuleTheme> = {
  "module-1": {
    tileClassName: "bg-blue-600 text-white",
    badgeClassName: "bg-blue-100 text-blue-700 dark:bg-blue-500/15 dark:text-blue-300",
  },
  "module-2": {
    tileClassName: "bg-purple-600 text-white",
    badgeClassName: "bg-purple-100 text-purple-700 dark:bg-purple-500/15 dark:text-purple-300",
  },
  "module-3": {
    tileClassName: "bg-orange-600 text-white",
    badgeClassName: "bg-orange-100 text-orange-700 dark:bg-orange-500/15 dark:text-orange-300",
  },
  "module-4": {
    tileClassName: "bg-teal-600 text-white",
    badgeClassName: "bg-teal-100 text-teal-700 dark:bg-teal-500/15 dark:text-teal-300",
  },
  "module-5": {
    tileClassName: "bg-red-600 text-white",
    badgeClassName: "bg-red-100 text-red-700 dark:bg-red-500/15 dark:text-red-300",
  },
  "module-6": {
    tileClassName: "bg-indigo-600 text-white",
    badgeClassName: "bg-indigo-100 text-indigo-700 dark:bg-indigo-500/15 dark:text-indigo-300",
  },
  "module-7": {
    tileClassName: "bg-pink-600 text-white",
    badgeClassName: "bg-pink-100 text-pink-700 dark:bg-pink-500/15 dark:text-pink-300",
  },
  "module-8": {
    tileClassName: "bg-amber-600 text-white",
    badgeClassName: "bg-amber-100 text-amber-700 dark:bg-amber-500/15 dark:text-amber-300",
  },
  "module-9": {
    tileClassName: "bg-cyan-600 text-white",
    badgeClassName: "bg-cyan-100 text-cyan-700 dark:bg-cyan-500/15 dark:text-cyan-300",
  },
};

// A plain grey fallback, used only if a module key doesn't match any of
// the themes above (shouldn't normally happen with exactly 9 modules).
const FALLBACK_THEME: ModuleTheme = {
  tileClassName: "bg-neutral-600 text-white",
  badgeClassName: "bg-neutral-100 text-neutral-700 dark:bg-neutral-500/15 dark:text-neutral-300",
};

export function getModuleTheme(moduleKey: string): ModuleTheme {
  return MODULE_THEMES_BY_KEY[moduleKey] ?? FALLBACK_THEME;
}

/** Pull the trailing number out of a module key, e.g. "module-3" -> "3". */
export function getModuleNumber(moduleKey: string): string {
  return moduleKey.split("-").at(-1) ?? "?";
}
