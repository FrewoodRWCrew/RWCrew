// How each phone-supported module looks on the landing page. Mirrors the
// web app's module-theme.ts (same colours), but only lists the modules the
// phone supports (see backend/app/mobile/registry.py). To add a module:
// add its key there and an entry here.

import type { Feather } from "@expo/vector-icons";
import type { ComponentProps, ComponentType } from "react";

import { RollContainerIcon } from "../components/roll-container-icon";

import type { TranslationKey } from "../i18n";

export type FeatherIconName = ComponentProps<typeof Feather>["name"];

export type ModuleTheme = {
  // The solid tile colour and the text colour readable on it.
  tileColor: string;
  onTileColor: string;
  // Feather's "box" is the same outline box as the web's lucide "Box" icon.
  icon: FeatherIconName;
  // A drawn icon used instead of `icon` when no Feather icon matches (the
  // same custom drawing the web tile uses).
  customIcon?: ComponentType<{ size: number; color: string }>;
  // The translation key of the module's name.
  titleKey: TranslationKey;
};

const MODULE_THEMES: Record<string, ModuleTheme> = {
  "module-2": {
    tileColor: "#9333ea", // Tailwind purple-600, the web tile colour of module-2
    onTileColor: "#ffffff",
    icon: "truck",
    // The web tile's rolcontainer drawing (Attachment/rolcontainer.jpg).
    customIcon: RollContainerIcon,
    titleKey: "karTracker.moduleTitle",
  },
  "module-3": {
    tileColor: "#ea580c", // Tailwind orange-600, the web tile colour of module-3
    onTileColor: "#ffffff",
    icon: "box",
    titleKey: "interventionRequests.moduleTitle",
  },
};

// A plain grey fallback for a module this app version doesn't know yet.
const FALLBACK_THEME: ModuleTheme = {
  tileColor: "#525252",
  onTileColor: "#ffffff",
  icon: "box",
  titleKey: "interventionRequests.moduleTitle",
};

export function getModuleTheme(moduleKey: string): ModuleTheme {
  return MODULE_THEMES[moduleKey] ?? FALLBACK_THEME;
}

// Whether this app version can open the module at all.
export function isKnownModule(moduleKey: string): boolean {
  return moduleKey in MODULE_THEMES;
}
