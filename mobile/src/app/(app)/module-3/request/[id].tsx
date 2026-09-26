// View or edit one existing intervention request. Users who may edit get a
// save button; users who may only view see the same form read-only. The
// request number and timestamp can never change.

import { Stack, useLocalSearchParams, useRouter } from "expo-router";
import { useState } from "react";

import { RequestForm } from "../../../../components/module-3/request-form";
import { useModule3Permissions } from "../../../../components/module-3/module-3-context";
import { ErrorView, Loading, describeError } from "../../../../components/ui";
import { useT } from "../../../../i18n";
import { module3Api } from "../../../../lib/module-api";
import type { InterventionRequestInput } from "../../../../lib/types";
import { useAsync } from "../../../../lib/use-async";

export default function EditRequestScreen() {
  const t = useT();
  const router = useRouter();
  const permissions = useModule3Permissions();
  const { id } = useLocalSearchParams<{ id: string }>();
  const requestId = Number(id);

  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);

  // The request itself plus the dropdown lists.
  const { data, error, loading, reload } = useAsync(async () => {
    const [request, lookups] = await Promise.all([module3Api.getRequest(requestId), module3Api.lookups()]);
    return { request, lookups };
  });

  async function handleSubmit(input: InterventionRequestInput) {
    setSubmitting(true);
    setSubmitError(null);
    try {
      await module3Api.updateRequest(requestId, input);
      router.back();
    } catch (caught) {
      setSubmitError(`${t("interventionRequests.requests.updateFailed")} ${describeError(caught, t)}`);
    } finally {
      setSubmitting(false);
    }
  }

  if (loading) return <Loading />;
  if (error || data === null) return <ErrorView error={error ?? new Error("No data")} onRetry={reload} />;

  const canEdit = permissions.can_edit_requests;

  return (
    <>
      {/* "Change request" when the user can edit, plain "Request" when read-only. */}
      <Stack.Screen
        options={{
          title: canEdit ? t("interventionRequests.requests.changeTitle") : t("interventionRequests.requests.viewTitle"),
        }}
      />
      <RequestForm
        initial={data.request}
        lookups={data.lookups}
        readOnly={!canEdit}
        submitting={submitting}
        submitError={submitError}
        submitLabel={t("common.save")}
        onSubmit={handleSubmit}
      />
    </>
  );
}
