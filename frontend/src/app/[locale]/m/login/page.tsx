// The phone's login page: the same login form as the desktop, but it leads
// to the phone's module tiles afterwards. Someone already logged in goes
// straight there.

import { getLocale } from "next-intl/server";
import { redirect } from "@/i18n/navigation";
import { getCurrentUserOnServer } from "@/lib/server-auth";
import { LoginForm } from "@/components/landing/login-form";
import { PHONE_HOME_HREF } from "@/components/phone/shared/phone-modules";

export default async function PhoneLoginPage() {
  const [user, locale] = await Promise.all([getCurrentUserOnServer(), getLocale()]);

  if (user) {
    redirect({ href: PHONE_HOME_HREF, locale });
  }

  return (
    <div className="flex flex-1 items-center justify-center p-4">
      <LoginForm redirectTo={PHONE_HOME_HREF} client="pwa" />
    </div>
  );
}
