// This file describes the languages RW Crew supports, in one shared
// place. Both the proxy (which decides which language to serve) and any
// links generated in the app (see navigation.ts) read this same config.

import { defineRouting } from "next-intl/routing";

export const routing = defineRouting({
  // The two languages the interface can be shown in.
  locales: ["nl", "en"],
  // Dutch is shown by default when a visitor hasn't chosen (or can't be
  // detected as preferring) a specific language, per RW Crew's
  // requirements.
  defaultLocale: "nl",
});

// A small helper type: the exact set of allowed locale strings ("nl" | "en").
export type AppLocale = (typeof routing.locales)[number];
