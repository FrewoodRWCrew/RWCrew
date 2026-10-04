// Every phone screen except the login page requires being logged in. Same
// server-side check as the desktop's (protected)/layout.tsx, but a visitor
// who isn't logged in goes to the phone's own login page.

import { getLocale } from "next-intl/server";
import { redirect } from "@/i18n/navigation";
import { getCurrentUserOnServer } from "@/lib/server-auth";
import { serverApiFetch } from "@/lib/server-api";
import type { Season } from "@/lib/types";
import { SeasonProvider } from "@/components/shared/season-provider";
import { PHONE_LOGIN_HREF } from "@/components/phone/shared/phone-modules";

export default async function PhoneSignedInLayout({ children }: { children: React.ReactNode }) {
  const [user, locale] = await Promise.all([getCurrentUserOnServer(), getLocale()]);

  if (!user) {
    redirect({ href: PHONE_LOGIN_HREF, locale });
    return null;
  }

  // The open years for the home page's year picker, fetched exactly like the
  // desktop layout does (only for users with module-9 access; an empty list
  // hides the picker and lets every tile open). The choice itself is shared
  // with the desktop through SeasonProvider's localStorage key.
  const seasons = user.accessible_module_keys.includes("module-9")
    ? await serverApiFetch<Season[]>("/api/modules/module-9/seasons").catch(() => [])
    : [];
  const openSeasons = seasons.filter((season) => season.periode_open);

  return <SeasonProvider seasons={openSeasons}>{children}</SeasonProvider>;
}
