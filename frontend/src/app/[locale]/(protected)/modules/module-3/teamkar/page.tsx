// Intervention Requests' "TeamKar" screen: every app user, with a checkbox
// to mark them as a member of TeamKar — see TeamKarManagement for the
// actual UI. Same server-fetch-then-render-client-component shape as
// intervention-statuses/page.tsx.

import { getTranslations } from "next-intl/server";
import { ServerApiError, serverApiFetch } from "@/lib/server-api";
import type { TeamKarUser } from "@/lib/types";
import { TeamKarManagement } from "@/components/module-3/teamkar-management";

export default async function TeamKarPage() {
  const tErrors = await getTranslations("errors");

  let users: TeamKarUser[] | null = null;
  try {
    users = await serverApiFetch<TeamKarUser[]>("/api/modules/module-3/teamkar/users");
  } catch (error) {
    if (error instanceof ServerApiError && error.status === 403) {
      return <p className="text-sm text-destructive">{tErrors("forbidden")}</p>;
    }
    throw error;
  }

  return <TeamKarManagement initialUsers={users} />;
}
