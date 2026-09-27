// Intervention Requests' "Settings > Mailing List" screen: the addresses
// that get an email (with the delivery-note PDF) for every new
// intervention request — see MailingListManagement for the actual UI.

import { getTranslations } from "next-intl/server";
import { ServerApiError, serverApiFetch } from "@/lib/server-api";
import type { MailingRecipient } from "@/lib/types";
import { MailingListManagement } from "@/components/module-3/mailing-list-management";

export default async function MailingListPage() {
  const tErrors = await getTranslations("errors");

  let recipients: MailingRecipient[] | null = null;
  try {
    recipients = await serverApiFetch<MailingRecipient[]>("/api/modules/module-3/mailing-list");
  } catch (error) {
    // No "view" right on the Mailing List screen → friendly message.
    if (error instanceof ServerApiError && error.status === 403) {
      return <p className="text-sm text-destructive">{tErrors("forbidden")}</p>;
    }
    throw error;
  }

  return <MailingListManagement initialRecipients={recipients} />;
}
