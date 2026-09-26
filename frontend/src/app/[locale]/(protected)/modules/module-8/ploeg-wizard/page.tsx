// Altsien Select's "Ploeg Wizard" entry screen: the teams the user may fill
// in, with their progress — see WizardTeamList. Gated by the
// "altsienselect.wizard" screen permission.

import { getTranslations } from "next-intl/server";
import { serverApiFetch } from "@/lib/server-api";
import type { AltsienSelectMyPermissions, AltsienSelectStep, Season } from "@/lib/types";
import { WizardTeamList } from "@/components/module-8/wizard/wizard-team-list";

export default async function PloegWizardPage() {
  const permissions = await serverApiFetch<AltsienSelectMyPermissions>("/api/modules/module-8/me/permissions");
  if (!permissions.viewable_screen_keys.includes("altsienselect.wizard")) {
    const tErrors = await getTranslations("errors");
    return <p className="text-sm text-destructive">{tErrors("forbidden")}</p>;
  }

  const [seasons, steps] = await Promise.all([
    serverApiFetch<Season[]>("/api/modules/module-8/seasons"),
    serverApiFetch<AltsienSelectStep[]>("/api/modules/module-8/steps"),
  ]);

  return (
    <WizardTeamList
      seasons={seasons}
      steps={steps}
      canViewPloegfiche={permissions.viewable_screen_keys.includes("altsienselect.ploegfiche")}
    />
  );
}
