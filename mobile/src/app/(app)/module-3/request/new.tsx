// Create a new intervention request. Only reachable for users whose web role
// allows creating (the "+" button is hidden otherwise, and the backend
// refuses anyway). The request number and timestamp are set by the backend.

import { useRouter } from "expo-router";
import { useState } from "react";

import { RequestForm } from "../../../../components/module-3/request-form";
import { useModule3Permissions } from "../../../../components/module-3/module-3-context";
import { ErrorView, Loading, describeError } from "../../../../components/ui";
import { useT } from "../../../../i18n";
import { module3Api } from "../../../../lib/module-api";
import type { InterventionRequestInput } from "../../../../lib/types";
import { useAsync } from "../../../../lib/use-async";

export default function NewRequestScreen() {
  const t = useT();
  const router = useRouter();
  const permissions = useModule3Permissions();
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);

  // The dropdown lists (statuses, teams, Team kar members).
  const { data: lookups, error, loading, reload } = useAsync(module3Api.lookups);

  async function handleSubmit(input: InterventionRequestInput) {
    setSubmitting(true);
    setSubmitError(null);
    try {
      await module3Api.createRequest(input);
      // Back to the list, which reloads and shows the new request.
      router.back();
    } catch (caught) {
      setSubmitError(`${t("interventionRequests.requests.createFailed")} ${describeError(caught, t)}`);
    } finally {
      setSubmitting(false);
    }
  }

  if (loading) return <Loading />;
  if (error || lookups === null) return <ErrorView error={error ?? new Error("No data")} onRetry={reload} />;

  return (
    <RequestForm
      initial={null}
      lookups={lookups}
      // A user without the create right just sees the (empty) form read-only.
      readOnly={!permissions.can_create_requests}
      submitting={submitting}
      submitError={submitError}
      submitLabel={t("common.create")}
      onSubmit={handleSubmit}
    />
  );
}
