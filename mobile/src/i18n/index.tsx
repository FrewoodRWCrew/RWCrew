// Tiny translation layer (Dutch + English). The language comes from the
// logged-in account's language preference (the same setting the web app
// uses); before login it follows the phone's language, defaulting to Dutch.

import { getLocales } from "expo-localization";
import { createContext, useContext, useMemo, type ReactNode } from "react";

import { useSession } from "../lib/session";
import { en } from "./en";
import { nl, type Dictionary } from "./nl";

export type Language = "nl" | "en";

// Every valid translation key as a "dotted.path" string, e.g. "landing.title".
type Paths<T, Prefix extends string = ""> = {
  [K in keyof T & string]: T[K] extends string ? `${Prefix}${K}` : Paths<T[K], `${Prefix}${K}.`>;
}[keyof T & string];
export type TranslationKey = Paths<Dictionary>;

const DICTIONARIES: Record<Language, Dictionary> = { nl, en };

type Translate = (key: TranslationKey, params?: Record<string, string | number>) => string;

const I18nContext = createContext<{ language: Language; t: Translate } | null>(null);

// The phone's own language, used before anyone is logged in.
function deviceLanguage(): Language {
  return getLocales()[0]?.languageCode === "en" ? "en" : "nl";
}

// Walk "a.b.c" down a dictionary; returns the key itself if it isn't found.
function lookup(dictionary: Dictionary, key: string): string {
  let node: unknown = dictionary;
  for (const part of key.split(".")) {
    if (typeof node !== "object" || node === null) return key;
    node = (node as Record<string, unknown>)[part];
  }
  return typeof node === "string" ? node : key;
}

export function I18nProvider({ children }: { children: ReactNode }) {
  const { user } = useSession();
  // The account's preference wins once logged in.
  const language: Language = user ? (user.language_preference === "en" ? "en" : "nl") : deviceLanguage();

  const value = useMemo(() => {
    const t: Translate = (key, params) => {
      let text = lookup(DICTIONARIES[language], key);
      // Fill in {placeholders}, e.g. "Hallo, {name}".
      for (const [name, replacement] of Object.entries(params ?? {})) {
        text = text.replaceAll(`{${name}}`, String(replacement));
      }
      return text;
    };
    return { language, t };
  }, [language]);

  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>;
}

export function useI18n() {
  const context = useContext(I18nContext);
  if (context === null) throw new Error("useI18n must be used inside <I18nProvider>");
  return context;
}

// Shortcut for screens that only need the translate function.
export function useT(): Translate {
  return useI18n().t;
}
