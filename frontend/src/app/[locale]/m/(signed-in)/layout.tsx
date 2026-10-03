// Every phone screen except the login page requires being logged in. Same
// server-side check as the desktop's (protected)/layout.tsx, but a visitor
// who isn't logged in goes to the phone's own login page.

import { getLocale } from "next-intl/server";
import { redirect } from "@/i18n/navigation";
import { getCurrentUserOnServer } from "@/lib/server-auth";
import { PHONE_LOGIN_HREF } from "@/components/phone/shared/phone-modules";

export default async function PhoneSignedInLayout({ children }: { children: React.ReactNode }) {
  const [user, locale] = await Promise.all([getCurrentUserOnServer(), getLocale()]);

  if (!user) {
    redirect({ href: PHONE_LOGIN_HREF, locale });
  }

  return <>{children}</>;
}
