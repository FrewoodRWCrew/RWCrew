// This file runs on the server for every page request. Its job is to
// figure out which language to use, and load that language's translated
// text (from the messages/*.json files) so pages and components can
// display it.

import { getRequestConfig } from "next-intl/server";
import { routing } from "./routing";

export default getRequestConfig(async ({ requestLocale }) => {
  // "requestLocale" comes from the URL segment (e.g. the "nl" in
  // "/nl/dashboard"), as decided by our proxy (see src/proxy.ts).
  const requested = await requestLocale;

  // Fall back to Dutch if the URL somehow has no language segment, or an
  // unsupported one — this should rarely happen because the proxy
  // normally redirects to a valid language first.
  const locale = routing.locales.includes(requested as (typeof routing.locales)[number])
    ? (requested as (typeof routing.locales)[number])
    : routing.defaultLocale;

  return {
    locale,
    // Load only the translation file for the chosen language.
    messages: (await import(`../../messages/${locale}.json`)).default,
  };
});
