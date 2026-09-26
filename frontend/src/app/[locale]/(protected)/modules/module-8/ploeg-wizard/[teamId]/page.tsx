// The Ploeg Wizard for one team (the season comes from "?season=", see
// AltsienSeasonSelect) — see TeamWizard. Gated by the "altsienselect.wizard"
// screen permission; whether this team is in the user's scope is checked
// by the backend (it answers 404 for someone else's team).

import { getTranslations } from "next-intl/server";
import { serverApiFetch } from "@/lib/server-api";
import type { AltsienSelectMyPermissions, Season } from "@/lib/types";
import { TeamWizard } from "@/components/module-8/wizard/team-wizard";

interface TeamWizardPageProps {
  params: Promise<{ teamId: string }>;
}

export default async function TeamWizardPage({ params }: TeamWizardPageProps) {
  const { teamId } = await params;
  const tErrors = await getTranslations("errors");

  const permissions = await serverApiFetch<AltsienSelectMyPermissions>("/api/modules/module-8/me/permissions");
  if (!permissions.viewable_screen_keys.includes("altsienselect.wizard") || !Number(teamId)) {
    return <p className="text-sm text-destructive">{tErrors("forbidden")}</p>;
  }

  const seasons = await serverApiFetch<Season[]>("/api/modules/module-8/seasons");

  return (
    <TeamWizard
      teamId={Number(teamId)}
      seasons={seasons}
      canViewPloegfiche={permissions.viewable_screen_keys.includes("altsienselect.ploegfiche")}
    />
  );
}
