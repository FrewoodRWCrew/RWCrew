// The whole screen shown when someone opens a phone module they have no
// access to: a plain header back to the tiles and the usual "no access" text.

import { getTranslations } from "next-intl/server";
import { PhoneBody } from "@/components/phone/shared/phone-body";
import { PhoneHeader } from "@/components/phone/shared/phone-header";
import { PHONE_HOME_HREF } from "@/components/phone/shared/phone-modules";
import { PhoneNotice } from "@/components/phone/shared/phone-notice";

export async function PhoneForbidden({ title }: { title: string }) {
  const [tErrors, tCommon] = await Promise.all([getTranslations("errors"), getTranslations("common")]);

  return (
    <>
      <PhoneHeader title={title} backHref={PHONE_HOME_HREF} backLabel={tCommon("back")} />
      <PhoneBody>
        <PhoneNotice>{tErrors("forbidden")}</PhoneNotice>
      </PhoneBody>
    </>
  );
}
