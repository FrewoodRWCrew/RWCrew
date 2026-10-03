"use client";

// "Uitloggen" on the phone home page: ends the session and goes back to the
// phone's own login page.

import { useTranslations } from "next-intl";
import { useRouter } from "@/i18n/navigation";
import { logout } from "@/lib/api";
import { PHONE_LOGIN_HREF } from "@/components/phone/shared/phone-modules";

export function PhoneLogoutButton() {
  const t = useTranslations("common");
  const router = useRouter();

  async function handleLogout() {
    // Even if the server can't be reached, leave for the login page.
    await logout().catch(() => undefined);
    router.replace(PHONE_LOGIN_HREF);
    router.refresh();
  }

  return (
    <button type="button" onClick={handleLogout} className="text-sm font-medium">
      {t("logout")}
    </button>
  );
}
