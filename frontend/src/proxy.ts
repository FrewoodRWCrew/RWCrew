// This is Next.js's "proxy" file (called "middleware" in older Next.js
// versions): a small piece of code that runs on the server before a page
// is rendered. We use it to detect which language the visitor should
// see, and make sure every URL has a language segment (e.g. redirecting
// bare "/" to "/nl").

import createIntlMiddleware from "next-intl/middleware";
import { routing } from "./i18n/routing";

// Build the actual proxy function from our language configuration.
export default createIntlMiddleware(routing);

export const config = {
  // Run on every page, but skip API routes, Next.js's own internal
  // static/image files, and common static asset file extensions — none
  // of those need a language prefix.
  matcher: ["/((?!api|_next|.*\\..*).*)"],
};
