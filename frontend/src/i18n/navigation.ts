// next-intl provides drop-in replacements for Next.js's own Link, router,
// and pathname helpers, that automatically understand our two-language
// URL structure (e.g. "/nl/modules/module-1" vs "/en/modules/module-1").
// The rest of the app should import Link/useRouter/etc. from HERE, not
// directly from "next/link" or "next/navigation", so links and redirects
// always keep the current language.

import { createNavigation } from "next-intl/navigation";
import { routing } from "./routing";

export const { Link, redirect, usePathname, useRouter, getPathname } = createNavigation(routing);
