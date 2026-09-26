// Altsien Select's "Opvolging aanvragen": the organisation's follow-up of
// every team's special requests — see RequestFollowUp. Gated by the
// "altsienselect.requests" screen permission.

import { getTranslations } from "next-intl/server";
import { serverApiFetch } from "@/lib/server-api";
import type { AltsienSelectMyPermissions, AltsienSelectRequestStatus, Season } from "@/lib/types";
import { RequestFollowUp } from "@/components/module-8/request-follow-up";

export default async function RequestFollowUpPage() {
  const permissions = await serverApiFetch<AltsienSelectMyPermissions>("/api/modules/module-8/me/permissions");
  if (!permissions.viewable_screen_keys.includes("altsienselect.requests")) {
    const tErrors = await getTranslations("errors");
    return <p className="text-sm text-destructive">{tErrors("forbidden")}</p>;
  }

  const [seasons, statuses] = await Promise.all([
    serverApiFetch<Season[]>("/api/modules/module-8/seasons"),
    serverApiFetch<AltsienSelectRequestStatus[]>("/api/modules/module-8/request-statuses"),
  ]);

  return <RequestFollowUp seasons={seasons} statuses={statuses} />;
}
