// Each of the 9 modules gets its own distinct accent colour, so tiles
// (and later, each module's own pages) are easy to tell apart at a
// glance. We reuse Tailwind's built-in colour scales — already tuned for
// good contrast — rather than inventing custom colours by hand.
//
// Once real module names/branding are decided, these colours (and their
// order) can simply be reassigned here without touching any component.

import { Box, Database, Nfc, Smartphone, type LucideIcon } from "lucide-react";
import type { CSSProperties } from "react";

import AltsienIcon from "@/components/icons/altsien-icon";
import RollContainerIcon from "@/components/icons/roll-container-icon";

export interface ModuleTheme {
  /** Classes for the module's tile on the landing page: a solid background
   *  covering the whole tile, plus a text colour readable on top of it. */
  tileClassName: string;
  /** Classes for the softer, pill-shaped badge shown on the module's own
   *  page (see ModulePlaceholderPage) — a light tint rather than solid fill. */
  badgeClassName: string;
  /** The same colour as tileClassName's background, as a bare Tailwind
   *  colour token (e.g. "blue-600") rather than a class — used to retint
   *  the active-sidebar-item/primary-button colour (normally the
   *  site-wide brand green) to this module's own accent once inside it,
   *  via getModuleAccentStyle() below. */
  accentColorToken: string;
  /** Bare Tailwind colour token used for readable text on the accent. */
  accentForegroundColorToken: string;
  /** A real icon for this module's tile, shown instead of its number.
   *  Left unset for modules that don't have one designed yet — those
   *  fall back to showing their plain number (see ModuleTile). */
  icon?: LucideIcon;
}

const MODULE_THEMES_BY_KEY: Record<string, ModuleTheme> = {
  "module-1": {
    tileClassName: "bg-blue-600 text-white",
    badgeClassName: "bg-blue-100 text-blue-700 dark:bg-blue-500/15 dark:text-blue-300",
    accentColorToken: "blue-600",
    accentForegroundColorToken: "white",
    // Tagscan reads RFID/contactless tags — lucide's "Nfc" icon is the
    // same "tag + radiating waves" contactless symbol, already drawn in
    // the same stroke style as every other icon used across the app.
    icon: Nfc,
  },
  "module-2": {
    tileClassName: "bg-purple-600 text-white",
    badgeClassName: "bg-purple-100 text-purple-700 dark:bg-purple-500/15 dark:text-purple-300",
    accentColorToken: "purple-600",
    accentForegroundColorToken: "white",
    // KarTracker manages the ~250 physical roll containers ("karren") used
    // for festival delivery planning — Attachment/rolcontainer.jpg is the
    // reference picture; no built-in lucide icon matches a wire-mesh roll
    // cage on casters, so this is a small custom one drawn in the same
    // stroke style (see src/components/icons/roll-container-icon.tsx).
    icon: RollContainerIcon,
  },
  "module-3": {
    tileClassName: "bg-orange-600 text-white",
    badgeClassName: "bg-orange-100 text-orange-700 dark:bg-orange-500/15 dark:text-orange-300",
    accentColorToken: "orange-600",
    accentForegroundColorToken: "neutral-950",
    // Intervention Requests' reference picture (Attachment/Box.png) is an
    // outline drawing of a cardboard box — lucide's "Box" icon is the same
    // shape, already drawn in the same stroke style as every other icon
    // used across the app.
    icon: Box,
  },
  "module-4": {
    tileClassName: "bg-teal-600 text-white",
    badgeClassName: "bg-teal-100 text-teal-700 dark:bg-teal-500/15 dark:text-teal-300",
    accentColorToken: "teal-600",
    accentForegroundColorToken: "neutral-950",
  },
  "module-5": {
    tileClassName: "bg-red-600 text-white",
    badgeClassName: "bg-red-100 text-red-700 dark:bg-red-500/15 dark:text-red-300",
    accentColorToken: "red-600",
    accentForegroundColorToken: "white",
  },
  "module-6": {
    tileClassName: "bg-indigo-600 text-white",
    badgeClassName: "bg-indigo-100 text-indigo-700 dark:bg-indigo-500/15 dark:text-indigo-300",
    accentColorToken: "indigo-600",
    accentForegroundColorToken: "white",
  },
  "module-7": {
    tileClassName: "bg-pink-600 text-white",
    badgeClassName: "bg-pink-100 text-pink-700 dark:bg-pink-500/15 dark:text-pink-300",
    accentColorToken: "pink-600",
    accentForegroundColorToken: "white",
  },
  "module-8": {
    tileClassName: "bg-fuchsia-600 text-white",
    badgeClassName: "bg-fuchsia-100 text-fuchsia-700 dark:bg-fuchsia-500/15 dark:text-fuchsia-300",
    accentColorToken: "fuchsia-600",
    accentForegroundColorToken: "white",
    // Altsien Select: a festive fuchsia no other module uses, with the
    // Altsien logo's swooping "A" as its icon.
    icon: AltsienIcon,
  },
  "module-9": {
    tileClassName: "bg-cyan-600 text-white",
    badgeClassName: "bg-cyan-100 text-cyan-700 dark:bg-cyan-500/15 dark:text-cyan-300",
    accentColorToken: "cyan-600",
    accentForegroundColorToken: "neutral-950",
    // MasterData's picture (Attachment/MasterData.jpg) shows a person
    // linked to two databases — lucide's "Database" icon captures the
    // same idea, and is already this app's own established icon for
    // "master data" (it was used for the admin sidebar's old Master Data
    // heading before that screen moved into this module).
    icon: Database,
  },
  "module-10": {
    tileClassName: "bg-emerald-600 text-white",
    badgeClassName: "bg-emerald-100 text-emerald-700 dark:bg-emerald-500/15 dark:text-emerald-300",
    accentColorToken: "emerald-600",
    accentForegroundColorToken: "white",
    // The web-side download page for the smartphone app.
    icon: Smartphone,
  },
};

// A plain grey fallback, used only if a module key doesn't match any of
// the themes above (shouldn't normally happen with exactly 9 modules).
const FALLBACK_THEME: ModuleTheme = {
  tileClassName: "bg-neutral-600 text-white",
  badgeClassName: "bg-neutral-100 text-neutral-700 dark:bg-neutral-500/15 dark:text-neutral-300",
  accentColorToken: "neutral-600",
  accentForegroundColorToken: "white",
};

export function getModuleTheme(moduleKey: string): ModuleTheme {
  return MODULE_THEMES_BY_KEY[moduleKey] ?? FALLBACK_THEME;
}

/**
 * CSS custom-property overrides that retint "primary"-coloured UI (the
 * active sidebar item, and every default-variant Button — "New role",
 * "New team", etc.) from the site-wide brand green to this module's own
 * accent colour instead, once applied to a wrapping element (see each
 * module's own layout.tsx). Every default-variant Button and the
 * sidebar's active-item highlight read colour from --primary/
 * --sidebar-primary (see globals.css) via Tailwind's bg-primary/
 * bg-sidebar-primary classes, so overriding those two custom properties
 * (plus their focus-ring counterparts, for the same reason globals.css
 * ties --ring/--sidebar-ring to the same green) is enough to retint every
 * such element inside — no need to touch each button/page individually.
 */
export function getModuleAccentStyle(moduleKey: string): CSSProperties {
  const theme = getModuleTheme(moduleKey);
  const accent = `var(--color-${theme.accentColorToken})`;
  const accentForeground = `var(--color-${theme.accentForegroundColorToken})`;
  const cssCustomProperties: Record<string, string> = {
    "--primary": accent,
    "--primary-foreground": accentForeground,
    "--sidebar-primary": accent,
    "--sidebar-primary-foreground": accentForeground,
    "--ring": accent,
    "--sidebar-ring": accent,
  };
  return cssCustomProperties as unknown as CSSProperties;
}

/** Pull the trailing number out of a module key, e.g. "module-3" -> "3". */
export function getModuleNumber(moduleKey: string): string {
  return moduleKey.split("-").at(-1) ?? "?";
}

// The landing page tile's label comes from the backend (see
// app/modules/registry.py), which only ever stores one, English name per
// module — so it can't be localized by itself. Modules that already have a
// real name also carry a translated "moduleTitle" in messages/*.json (used
// in their own sidebar); this maps a module key to that translation key so
// the landing tile can show the localized name instead. Placeholder
// modules ("Module 2", "Module 4".."Module 8") have no entry here and fall
// back to the backend's name as-is, since "Module 2" reads the same in
// every locale anyway.
const MODULE_TRANSLATION_KEYS: Record<string, string> = {
  "module-1": "tagscan.moduleTitle",
  "module-2": "karTracker.moduleTitle",
  "module-3": "interventionRequests.moduleTitle",
  "module-8": "altsienSelect.moduleTitle",
  "module-9": "masterdata.moduleTitle",
};

export function getModuleTranslationKey(moduleKey: string): string | undefined {
  return MODULE_TRANSLATION_KEYS[moduleKey];
}
