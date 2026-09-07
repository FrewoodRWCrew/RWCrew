"use client";

// The actual interactive public intervention-request form — no login, no
// staff-only fields (status/handled-by/team-kar are set by the backend
// itself, see app/modules/module_3/public_router.py). Pre-filled from the
// page's `defaults` (the QR code's query parameters) but every field stays
// editable, since a customer may need to correct stale QR data.

import { useState, type FormEvent } from "react";
import { useTranslations } from "next-intl";
import { ApiError, submitPublicInterventionRequest } from "@/lib/api";
import type { InterventionRequestsTeam, PublicInterventionRequestInput } from "@/lib/types";
import { formatPhoneNumber } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { TeamCombobox } from "./team-combobox";

interface PublicInterventionRequestFormProps {
  teams: InterventionRequestsTeam[];
  defaults: {
    team_id: number | null;
    team_name: string | null;
    cart_number: string | null;
    delivery_location: string | null;
    zone: string | null;
  };
}

const EMPTY_FIELDS = {
  question: "",
  employee_name: "",
  employee_phone: "",
  preferred_delivery_at: "",
};

export function PublicInterventionRequestForm({ teams, defaults }: PublicInterventionRequestFormProps) {
  const t = useTranslations("interventionRequestPublicForm");
  // Field labels are the same wording as the staff admin dialog, so they're
  // reused from that namespace rather than duplicated here.
  const tFields = useTranslations("interventionRequests.requests");

  const [teamId, setTeamId] = useState(defaults.team_id);
  const [teamName, setTeamName] = useState(defaults.team_name);
  const [cartNumber, setCartNumber] = useState(defaults.cart_number ?? "");
  const [deliveryLocation, setDeliveryLocation] = useState(defaults.delivery_location ?? "");
  const [zone, setZone] = useState(defaults.zone ?? "");
  const [fields, setFields] = useState(EMPTY_FIELDS);

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [submittedRequestNumber, setSubmittedRequestNumber] = useState<string | null>(null);

  function updateField<K extends keyof typeof EMPTY_FIELDS>(field: K, value: (typeof EMPTY_FIELDS)[K]) {
    setFields((current) => ({ ...current, [field]: value }));
  }

  function resetForNewRequest() {
    setTeamId(null);
    setTeamName(null);
    setCartNumber("");
    setDeliveryLocation("");
    setZone("");
    setFields(EMPTY_FIELDS);
    setSubmittedRequestNumber(null);
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setErrorMessage(null);
    setIsSubmitting(true);

    const payload: PublicInterventionRequestInput = {
      team_id: teamId,
      team_name: teamName,
      cart_number: cartNumber || null,
      question: fields.question,
      employee_name: fields.employee_name || null,
      employee_phone: fields.employee_phone || null,
      preferred_delivery_at: fields.preferred_delivery_at || null,
      delivery_location: deliveryLocation || null,
      zone: zone || null,
    };

    try {
      const created = await submitPublicInterventionRequest(payload);
      setSubmittedRequestNumber(created.request_number);
    } catch (error) {
      setErrorMessage(error instanceof ApiError ? error.message : t("errorMessage"));
    } finally {
      setIsSubmitting(false);
    }
  }

  const canSubmit = Boolean((teamId || teamName?.trim()) && fields.question.trim());

  if (submittedRequestNumber) {
    return (
      <Card className="w-full max-w-lg">
        <CardHeader>
          <CardTitle>{t("successTitle")}</CardTitle>
          <CardDescription>{t("successMessage", { requestNumber: submittedRequestNumber })}</CardDescription>
        </CardHeader>
        <CardContent>
          <Button variant="outline" onClick={resetForNewRequest}>
            {t("newRequestButton")}
          </Button>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="w-full max-w-lg">
      <CardHeader>
        <CardTitle>{t("title")}</CardTitle>
        <CardDescription>{t("description")}</CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <TeamCombobox
            id="public-request-team"
            label={tFields("associationNameLabel")}
            teams={teams}
            teamId={teamId}
            teamName={teamName}
            otherOptionLabel={tFields("otherTeamOption")}
            otherPlaceholder={tFields("teamNamePlaceholder")}
            onChange={(next) => {
              setTeamId(next.team_id);
              setTeamName(next.team_name);
            }}
          />

          <div className="flex flex-col gap-2">
            <Label htmlFor="public-request-cart-number">{tFields("cartNumberLabel")}</Label>
            <Input
              id="public-request-cart-number"
              value={cartNumber}
              onChange={(event) => setCartNumber(event.target.value)}
            />
          </div>

          <div className="flex flex-col gap-2">
            <Label htmlFor="public-request-delivery-location">{tFields("deliveryLocationLabel")}</Label>
            <Input
              id="public-request-delivery-location"
              value={deliveryLocation}
              onChange={(event) => setDeliveryLocation(event.target.value)}
            />
          </div>

          <div className="flex flex-col gap-2">
            <Label htmlFor="public-request-zone">{tFields("zoneLabel")}</Label>
            <Input id="public-request-zone" value={zone} onChange={(event) => setZone(event.target.value)} />
          </div>

          <div className="flex flex-col gap-2">
            <Label htmlFor="public-request-question">{tFields("questionLabel")}</Label>
            <Textarea
              id="public-request-question"
              required
              value={fields.question}
              onChange={(event) => updateField("question", event.target.value)}
            />
          </div>

          <div className="flex flex-col gap-2">
            <Label htmlFor="public-request-employee-name">{tFields("employeeNameLabel")}</Label>
            <Input
              id="public-request-employee-name"
              value={fields.employee_name}
              onChange={(event) => updateField("employee_name", event.target.value)}
            />
          </div>

          <div className="flex flex-col gap-2">
            <Label htmlFor="public-request-employee-phone">{tFields("employeePhoneLabel")}</Label>
            <Input
              id="public-request-employee-phone"
              type="tel"
              value={fields.employee_phone}
              onChange={(event) => updateField("employee_phone", formatPhoneNumber(event.target.value))}
            />
          </div>

          <div className="flex flex-col gap-2">
            <Label htmlFor="public-request-preferred-delivery">{tFields("preferredDeliveryAtLabel")}</Label>
            <Input
              id="public-request-preferred-delivery"
              type="datetime-local"
              value={fields.preferred_delivery_at}
              onChange={(event) => updateField("preferred_delivery_at", event.target.value)}
            />
          </div>

          {errorMessage && <p className="text-sm text-destructive">{errorMessage}</p>}

          <Button type="submit" disabled={isSubmitting || !canSubmit}>
            {isSubmitting ? t("submitting") : t("submitButton")}
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}
