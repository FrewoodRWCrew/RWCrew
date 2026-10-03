// The phone home page: a greeting, "Uitloggen", and one big tile per module
// that has a phone version and that this user may open.

import { getTranslations } from "next-intl/server";
import { getCurrentUserOnServer } from "@/lib/server-auth";
import { serverApiFetch } from "@/lib/server-api";
import { getModuleTranslationKey } from "@/lib/module-theme";
import type { ModuleInfo } from "@/lib/types";
import { PhoneBody } from "@/components/phone/shared/phone-body";
import { PhoneHeader } from "@/components/phone/shared/phone-header";
import { PhoneLogoutButton } from "@/components/phone/shared/phone-logout-button";
import { PHONE_MODULE_KEYS } from "@/components/phone/shared/phone-modules";
import { PhoneNotice } from "@/components/phone/shared/phone-notice";
import { PhoneTileGrid } from "@/components/phone/shared/phone-tile-grid";

export default async function PhoneHomePage() {
  const [t, tPhone, tRoot] = await Promise.all([
    getTranslations("landing"),
    getTranslations("phone"),
    getTranslations(),
  ]);
  const [user, modules] = await Promise.all([getCurrentUserOnServer(), serverApiFetch<ModuleInfo[]>("/api/modules")]);

  // Only modules with a phone version that this user has access to, in
  // their usual order and with their translated names (as on the desktop).
  const accessibleKeys = new Set(user?.accessible_module_keys ?? []);
  const phoneModules = modules
    .filter((module) => PHONE_MODULE_KEYS.includes(module.key) && accessibleKeys.has(module.key))
    .sort((a, b) => a.sort_order - b.sort_order)
    .map((module) => {
      const translationKey = getModuleTranslationKey(module.key);
      return translationKey ? { ...module, name: tRoot(translationKey) } : module;
    });

  return (
    <>
      <PhoneHeader title={t("title")} action={<PhoneLogoutButton />} />
      <PhoneBody>
        <div>
          <p className="text-sm text-muted-foreground">{tPhone("hello", { name: user?.display_name ?? "" })}</p>
          <p className="text-muted-foreground">{t("subtitle")}</p>
        </div>
        {phoneModules.length === 0 ? <PhoneNotice>{t("noAccess")}</PhoneNotice> : <PhoneTileGrid modules={phoneModules} />}
      </PhoneBody>
    </>
  );
}
