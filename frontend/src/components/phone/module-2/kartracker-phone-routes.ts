// The addresses of KarTracker's phone screens, in one place so screens link
// to each other without spelling out URLs.

import { phoneModuleHref } from "@/components/phone/shared/phone-modules";

const BASE_HREF = phoneModuleHref("module-2");

export const karTrackerPhoneRoutes = {
  menu: BASE_HREF,
  scan: `${BASE_HREF}/scan`,
  planning: `${BASE_HREF}/planning`,
  /** The map; with a pin key (e.g. "kar-12") it flies to that pin on opening. */
  map: (focusKey?: string) => (focusKey ? `${BASE_HREF}/map?focus=${encodeURIComponent(focusKey)}` : `${BASE_HREF}/map`),
  /** One kar's movement form, by its kar number. */
  kar: (karNummer: string) => `${BASE_HREF}/kar/${encodeURIComponent(karNummer)}`,
};
