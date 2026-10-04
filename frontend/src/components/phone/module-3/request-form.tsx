"use client";

// The phone's request form, for a new request or an existing one: the same
// fields as the desktop dialog, one under the other, with the phone's own
// pickers for choices and the delivery date. Without the right to save it
// is shown read-only. Deleting and the PDF stay desktop-only.

import { useState, type FormEvent } from "react";
import { Phone } from "lucide-react";
import { useTranslations } from "next-intl";
import { toast } from "sonner";
import { useRouter } from "@/i18n/navigation";
import { ApiError, createInterventionRequest, updateInterventionRequest } from "@/lib/api";
import type { InterventionRequest, InterventionRequestInput, InterventionRequestsLookups } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { defaultStatusId, formatDateTime, toDateTimeLocalValue } from "@/components/module-3/request-dates";
import { interventionRequestsPhoneRoutes } from "@/components/phone/module-3/intervention-requests-phone-routes";
import { PhoneSelect } from "@/components/phone/shared/phone-select";

// The "Ploeg" choice for a team that isn't in the list (typed by name).
const OTHER_TEAM = "other";

interface RequestFormProps {
  /** The request being viewed/edited; left out for a new one. */
  request?: InterventionRequest;
  lookups: InterventionRequestsLookups;
  /** Whether this user may save (create for a new one, edit otherwise). */
  canSave: boolean;
}

/** Everything in the form as plain text, the way the inputs hold it. */
interface FormValues {
  /** A team id as text, OTHER_TEAM, or "" for nothing chosen yet. */
  teamChoice: string;
  teamName: string;
  cartNumber: string;
  question: string;
  employeeName: string;
  employeePhone: string;
  preferredDeliveryAt: string;
  deliveryLocation: string;
  zone: string;
  statusId: string;
  handledBy: string;
  teamCartUserId: string;
}

/** The form's starting values: the request's, or empty with the "Nieuw" status. */
function initialValues(request: InterventionRequest | undefined, lookups: InterventionRequestsLookups): FormValues {
  // A typed team name (from the public form) shows as "Andere" + that name.
  const teamChoice = request ? (request.team_id !== null ? String(request.team_id) : request.team_name ? OTHER_TEAM : "") : "";
  const statusId = request?.status_id ?? (defaultStatusId(lookups.statuses) || lookups.statuses[0]?.id);
  return {
    teamChoice,
    teamName: request?.team_name ?? "",
    cartNumber: request?.cart_number ?? "",
    question: request?.question ?? "",
    employeeName: request?.employee_name ?? "",
    employeePhone: request?.employee_phone ?? "",
    preferredDeliveryAt: toDateTimeLocalValue(request?.preferred_delivery_at ?? null),
    deliveryLocation: request?.delivery_location ?? "",
    zone: request?.zone ?? "",
    statusId: statusId ? String(statusId) : "",
    handledBy: request?.handled_by ?? "",
    teamCartUserId: request?.team_cart_user_id ? String(request.team_cart_user_id) : "",
  };
}

/** Empty text becomes null, so the backend stores "nothing" instead of "". */
function textOrNull(value: string): string | null {
  const trimmed = value.trim();
  return trimmed ? trimmed : null;
}

export function RequestForm({ request, lookups, canSave }: RequestFormProps) {
  const t = useTranslations("interventionRequests.requests");
  const tPhone = useTranslations("interventionRequests.phone");
  const tCommon = useTranslations("common");
  const router = useRouter();
  const [values, setValues] = useState(() => initialValues(request, lookups));
  // Validation messages only appear after the first save attempt.
  const [showErrors, setShowErrors] = useState(false);
  const [isSaving, setIsSaving] = useState(false);

  function update<K extends keyof FormValues>(field: K, value: FormValues[K]) {
    setValues((current) => ({ ...current, [field]: value }));
  }

  // The three required things: a question, a ploeg (from the list or typed), a status.
  const questionMissing = !values.question.trim();
  const teamMissing = !values.teamChoice || (values.teamChoice === OTHER_TEAM && !values.teamName.trim());
  const statusMissing = !values.statusId;

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setShowErrors(true);
    if (questionMissing || teamMissing || statusMissing) return;

    // A list team sends only its id; "Andere" sends only the typed name.
    const isOtherTeam = values.teamChoice === OTHER_TEAM;
    const payload: InterventionRequestInput = {
      team_id: isOtherTeam ? null : Number(values.teamChoice),
      team_name: isOtherTeam ? textOrNull(values.teamName) : null,
      cart_number: textOrNull(values.cartNumber),
      question: values.question.trim(),
      employee_name: textOrNull(values.employeeName),
      employee_phone: textOrNull(values.employeePhone),
      preferred_delivery_at: values.preferredDeliveryAt || null,
      delivery_location: textOrNull(values.deliveryLocation),
      zone: textOrNull(values.zone),
      status_id: Number(values.statusId),
      handled_by: textOrNull(values.handledBy),
      team_cart_user_id: values.teamCartUserId ? Number(values.teamCartUserId) : null,
    };

    setIsSaving(true);
    try {
      if (request) await updateInterventionRequest(request.id, payload);
      else await createInterventionRequest(payload);
      toast.success(request ? t("requestUpdated") : t("requestCreated"));
      // Back to the list, which loads afresh with the change in it.
      router.push(interventionRequestsPhoneRoutes.requests);
      router.refresh();
    } catch (error) {
      const failed = request ? t("updateFailed") : t("createFailed");
      toast.error(error instanceof ApiError ? `${failed} ${error.message}` : failed);
      setIsSaving(false);
    }
  }

  const readOnly = !canSave;

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-4">
      {readOnly && <p className="text-sm text-muted-foreground italic">{tPhone("readOnlyNotice")}</p>}

      {/* An existing request's number and when it came in. */}
      {request && (
        <div>
          <p className="text-xl font-bold">{request.request_number}</p>
          <p className="text-sm text-muted-foreground">
            {t("columnSubmittedAt")}: {formatDateTime(request.submitted_at)}
          </p>
        </div>
      )}

      {/* Fieldset switches every input to read-only in one go. */}
      <fieldset disabled={readOnly || isSaving} className="flex flex-col gap-4">
        <Field label={t("associationNameLabel")} htmlFor="phone-request-team" error={showErrors && teamMissing ? tPhone("teamRequired") : null}>
          <PhoneSelect id="phone-request-team" value={values.teamChoice} onChange={(event) => update("teamChoice", event.target.value)}>
            <option value="">{tPhone("choose")}</option>
            {lookups.teams.map((team) => (
              <option key={team.id} value={team.id}>
                {team.name}
              </option>
            ))}
            <option value={OTHER_TEAM}>{t("otherTeamOption")}</option>
          </PhoneSelect>
          {values.teamChoice === OTHER_TEAM && (
            <Input
              value={values.teamName}
              onChange={(event) => update("teamName", event.target.value)}
              placeholder={t("teamNamePlaceholder")}
              className="h-11 text-base"
            />
          )}
        </Field>

        <Field label={t("cartNumberLabel")} htmlFor="phone-request-cart">
          <Input id="phone-request-cart" value={values.cartNumber} onChange={(event) => update("cartNumber", event.target.value)} className="h-11 text-base" />
        </Field>

        <Field label={t("questionLabel")} htmlFor="phone-request-question" error={showErrors && questionMissing ? tPhone("questionRequired") : null}>
          <Textarea
            id="phone-request-question"
            value={values.question}
            onChange={(event) => update("question", event.target.value)}
            rows={4}
            className="text-base"
          />
        </Field>

        <Field label={t("employeeNameLabel")} htmlFor="phone-request-employee">
          <Input id="phone-request-employee" value={values.employeeName} onChange={(event) => update("employeeName", event.target.value)} className="h-11 text-base" />
        </Field>

        <Field label={t("employeePhoneLabel")} htmlFor="phone-request-phone">
          <Input
            id="phone-request-phone"
            type="tel"
            value={values.employeePhone}
            onChange={(event) => update("employeePhone", event.target.value)}
            className="h-11 text-base"
          />
          {/* One tap to call the employee. */}
          {values.employeePhone.trim() && (
            <a href={`tel:${values.employeePhone.trim()}`} className="flex items-center gap-1.5 text-sm font-medium text-primary">
              <Phone className="size-4" />
              {values.employeePhone.trim()}
            </a>
          )}
        </Field>

        <Field label={t("preferredDeliveryAtLabel")} htmlFor="phone-request-delivery">
          <Input
            id="phone-request-delivery"
            type="datetime-local"
            value={values.preferredDeliveryAt}
            onChange={(event) => update("preferredDeliveryAt", event.target.value)}
            className="h-11 text-base"
          />
        </Field>

        <Field label={t("deliveryLocationLabel")} htmlFor="phone-request-location">
          <Input id="phone-request-location" value={values.deliveryLocation} onChange={(event) => update("deliveryLocation", event.target.value)} className="h-11 text-base" />
        </Field>

        <Field label={t("zoneLabel")} htmlFor="phone-request-zone">
          <Input id="phone-request-zone" value={values.zone} onChange={(event) => update("zone", event.target.value)} className="h-11 text-base" />
        </Field>

        <Field label={t("statusLabel")} htmlFor="phone-request-status">
          <PhoneSelect id="phone-request-status" value={values.statusId} onChange={(event) => update("statusId", event.target.value)}>
            {lookups.statuses.map((status) => (
              <option key={status.id} value={status.id}>
                {status.name}
              </option>
            ))}
          </PhoneSelect>
        </Field>

        <Field label={t("handledByLabel")} htmlFor="phone-request-handled-by">
          <Input id="phone-request-handled-by" value={values.handledBy} onChange={(event) => update("handledBy", event.target.value)} className="h-11 text-base" />
        </Field>

        <Field label={t("teamCartLabel")} htmlFor="phone-request-team-cart">
          <PhoneSelect id="phone-request-team-cart" value={values.teamCartUserId} onChange={(event) => update("teamCartUserId", event.target.value)}>
            <option value="">{t("noneOption")}</option>
            {lookups.teamkar_members.map((member) => (
              <option key={member.id} value={member.id}>
                {member.display_name}
              </option>
            ))}
          </PhoneSelect>
        </Field>
      </fieldset>

      {canSave && (
        <Button type="submit" className="h-12 text-base" disabled={isSaving}>
          {isSaving ? tCommon("loading") : request ? tCommon("save") : tCommon("create")}
        </Button>
      )}
    </form>
  );
}

interface FieldProps {
  label: string;
  htmlFor: string;
  /** A validation message under the field, if any. */
  error?: string | null;
  children: React.ReactNode;
}

/** A label, the input(s) and an optional validation message. */
function Field({ label, htmlFor, error, children }: FieldProps) {
  return (
    <div className="flex flex-col gap-2">
      <Label htmlFor={htmlFor}>{label}</Label>
      {children}
      {error && <p className="text-sm text-destructive">{error}</p>}
    </div>
  );
}
