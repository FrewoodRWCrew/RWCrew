// The modules that have a phone version (the "/m/..." section of the PWA).
// This list is the one place to add a module to the phone's tile grid; its
// screens then live in app/[locale]/m/(signed-in)/module-N/ and
// components/phone/module-N/ (see CLAUDE.md, "Phone section (PWA)").

export const PHONE_MODULE_KEYS: readonly string[] = ["module-2", "module-3"];

/** The phone home page, with the module tiles. */
export const PHONE_HOME_HREF = "/m";

/** The phone's own login page. */
export const PHONE_LOGIN_HREF = "/m/login";

/** Where a module's phone screens start, e.g. "/m/module-3". */
export function phoneModuleHref(moduleKey: string): string {
  return `${PHONE_HOME_HREF}/${moduleKey}`;
}
