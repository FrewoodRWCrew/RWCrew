// Altsien Select's "Ploegfiche": one team's complete overview of its wizard
// choices, plus the PDF button — see Ploegfiche. Gated by the
// "altsienselect.ploegfiche" screen permission.

import { getTranslations } from "next-intl/server";
import { serverApiFetch } from "@/lib/server-api";
import type { AltsienSelectMyPermissions, Season } from "@/lib/types";
import { Ploegfiche } from "@/components/module-8/ploegfiche";

export default async function PloegfichePage() {
  const permissions = await serverApiFetch<AltsienSelectMyPermissions>("/api/modules/module-8/me/permissions");
  if (!permissions.viewable_screen_keys.includes("altsienselect.ploegfiche")) {
    const tErrors = await getTranslations("errors");
    return <p className="text-sm text-destructive">{tErrors("forbidden")}</p>;
  }

  const seasons = await serverApiFetch<Season[]>("/api/modules/module-8/seasons");

  return (
    <Ploegfiche
      seasons={seasons}
      canOpenWizard={permissions.viewable_screen_keys.includes("altsienselect.wizard")}
    />
  );
}
