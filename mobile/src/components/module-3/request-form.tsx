// The form used to create a new request and to view/edit an existing one.
// The fields mirror the web app's request form. It only builds the data and
// hands it to onSubmit; the screen decides what to do with it (create or
// update). When the user may not edit, every field is read-only and there is
// no save button.

import { Feather } from "@expo/vector-icons";
import { useState } from "react";
import { Linking, Pressable, ScrollView, StyleSheet, Text, View } from "react-native";

import { useI18n } from "../../i18n";
import type { Dictionary } from "../../i18n/nl";
import { useColors } from "../../lib/theme";
import type { InterventionRequest, InterventionRequestInput, Lookups } from "../../lib/types";
import { DateTimeField } from "../date-time-field";
import { SelectField } from "../select-field";
import { Button, TextField } from "../ui";
import { formatDateTime } from "./format";

// Every text key of the requests screen, e.g. "questionLabel".
type RequestKey = keyof Dictionary["interventionRequests"]["requests"];

// The team dropdown's "Other (not in the list)" entry.
const OTHER_TEAM = "other";

type FormState = {
  // A MasterData team id, "other" (free text below), or null (not chosen yet).
  team: number | typeof OTHER_TEAM | null;
  teamName: string;
  cartNumber: string;
  question: string;
  employeeName: string;
  employeePhone: string;
  preferredDeliveryAt: string | null;
  deliveryLocation: string;
  zone: string;
  statusId: number | null;
  handledBy: string;
  teamCartUserId: number | null;
};

// Starting values: the existing request's, or sensible blanks for a new one.
function initialState(initial: InterventionRequest | null, lookups: Lookups): FormState {
  if (initial) {
    return {
      team: initial.team_id ?? (initial.team_name ? OTHER_TEAM : null),
      teamName: initial.team_name ?? "",
      cartNumber: initial.cart_number ?? "",
      question: initial.question,
      employeeName: initial.employee_name ?? "",
      employeePhone: initial.employee_phone ?? "",
      preferredDeliveryAt: initial.preferred_delivery_at,
      deliveryLocation: initial.delivery_location ?? "",
      zone: initial.zone ?? "",
      statusId: initial.status_id,
      handledBy: initial.handled_by ?? "",
      teamCartUserId: initial.team_cart_user_id,
    };
  }
  // New requests start in the "Nieuw" status (like the web form), else the first one.
  const defaultStatus = lookups.statuses.find((status) => status.name === "Nieuw") ?? lookups.statuses[0];
  return {
    team: null,
    teamName: "",
    cartNumber: "",
    question: "",
    employeeName: "",
    employeePhone: "",
    preferredDeliveryAt: null,
    deliveryLocation: "",
    zone: "",
    statusId: defaultStatus?.id ?? null,
    handledBy: "",
    teamCartUserId: null,
  };
}

// An empty/whitespace text becomes null, like the web form does.
function orNull(text: string): string | null {
  const trimmed = text.trim();
  return trimmed === "" ? null : trimmed;
}

type Props = {
  initial: InterventionRequest | null;
  lookups: Lookups;
  readOnly: boolean;
  submitting: boolean;
  submitError: string | null;
  submitLabel: string;
  onSubmit: (input: InterventionRequestInput) => void;
};

export function RequestForm({ initial, lookups, readOnly, submitting, submitError, submitLabel, onSubmit }: Props) {
  const { t, language } = useI18n();
  const colors = useColors();
  const [form, setForm] = useState<FormState>(() => initialState(initial, lookups));
  const [showErrors, setShowErrors] = useState(false);

  // Update one field, leaving the others as they are.
  function set<K extends keyof FormState>(key: K, value: FormState[K]) {
    setForm((current) => ({ ...current, [key]: value }));
  }

  // The same rules as the backend: a question, exactly one team reference, a status.
  const questionMissing = form.question.trim() === "";
  const teamMissing = form.team === null || (form.team === OTHER_TEAM && form.teamName.trim() === "");
  const statusMissing = form.statusId === null;

  function handleSubmit() {
    setShowErrors(true);
    if (questionMissing || teamMissing || statusMissing) return;
    onSubmit({
      team_id: typeof form.team === "number" ? form.team : null,
      // Free text is only sent when "Other" is chosen (never both).
      team_name: form.team === OTHER_TEAM ? form.teamName.trim() : null,
      cart_number: orNull(form.cartNumber),
      question: form.question.trim(),
      employee_name: orNull(form.employeeName),
      employee_phone: orNull(form.employeePhone),
      preferred_delivery_at: form.preferredDeliveryAt,
      delivery_location: orNull(form.deliveryLocation),
      zone: orNull(form.zone),
      status_id: form.statusId as number,
      handled_by: orNull(form.handledBy),
      team_cart_user_id: form.teamCartUserId,
    });
  }

  // Translate a key of the requests screen ("questionLabel", ...), checked by TypeScript.
  const tr = (key: RequestKey) => t(`interventionRequests.requests.${key}` as const);
  const editable = !readOnly;

  return (
    <ScrollView contentContainerStyle={styles.content} keyboardShouldPersistTaps="handled">
      {readOnly && <Text style={[styles.notice, { color: colors.muted }]}>{tr("readOnlyNotice")}</Text>}

      {initial && (
        <View style={styles.meta}>
          <Text style={[styles.metaNumber, { color: colors.text }]}>{initial.request_number}</Text>
          <Text style={{ color: colors.muted }}>
            {tr("submittedAt")}: {formatDateTime(initial.submitted_at, language)}
          </Text>
        </View>
      )}

      <SelectField<number | typeof OTHER_TEAM>
        label={tr("associationNameLabel")}
        value={form.team}
        editable={editable}
        options={[
          ...lookups.teams.map((team) => ({ value: team.id as number | typeof OTHER_TEAM, label: team.name })),
          { value: OTHER_TEAM, label: tr("otherTeamOption") },
        ]}
        onChange={(value) => set("team", value)}
      />
      {form.team === OTHER_TEAM && (
        <TextField
          label={tr("teamNamePlaceholder")}
          value={form.teamName}
          editable={editable}
          onChangeText={(text) => set("teamName", text)}
        />
      )}
      {showErrors && teamMissing && <Text style={{ color: colors.danger }}>{tr("teamRequired")}</Text>}

      <TextField
        label={tr("cartNumberLabel")}
        value={form.cartNumber}
        editable={editable}
        onChangeText={(text) => set("cartNumber", text)}
      />
      <TextField
        label={tr("questionLabel")}
        value={form.question}
        editable={editable}
        multiline
        autoCapitalize="sentences"
        onChangeText={(text) => set("question", text)}
        error={showErrors && questionMissing ? tr("questionRequired") : null}
      />
      <TextField
        label={tr("employeeNameLabel")}
        value={form.employeeName}
        editable={editable}
        onChangeText={(text) => set("employeeName", text)}
      />
      <TextField
        label={tr("employeePhoneLabel")}
        value={form.employeePhone}
        editable={editable}
        keyboardType="phone-pad"
        onChangeText={(text) => set("employeePhone", text)}
      />
      {/* Tap to call the employee — handy in the field. */}
      {form.employeePhone.trim() !== "" && (
        <Pressable style={styles.call} onPress={() => Linking.openURL(`tel:${form.employeePhone.trim()}`)}>
          <Feather name="phone" size={16} color={colors.brand} />
          <Text style={{ color: colors.brand, fontWeight: "600" }}>{form.employeePhone.trim()}</Text>
        </Pressable>
      )}

      <DateTimeField
        label={tr("preferredDeliveryAtLabel")}
        value={form.preferredDeliveryAt}
        editable={editable}
        onChange={(value) => set("preferredDeliveryAt", value)}
      />
      <TextField
        label={tr("deliveryLocationLabel")}
        value={form.deliveryLocation}
        editable={editable}
        onChangeText={(text) => set("deliveryLocation", text)}
      />
      <TextField
        label={tr("zoneLabel")}
        value={form.zone}
        editable={editable}
        onChangeText={(text) => set("zone", text)}
      />

      <SelectField<number>
        label={tr("statusLabel")}
        value={form.statusId}
        editable={editable}
        options={lookups.statuses.map((status) => ({ value: status.id, label: status.name }))}
        onChange={(value) => set("statusId", value)}
      />
      <TextField
        label={tr("handledByLabel")}
        value={form.handledBy}
        editable={editable}
        onChangeText={(text) => set("handledBy", text)}
      />
      <SelectField<number>
        label={tr("teamCartLabel")}
        value={form.teamCartUserId}
        editable={editable}
        noneLabel={tr("noneOption")}
        options={lookups.teamkar_members.map((member) => ({ value: member.id, label: member.display_name }))}
        onChange={(value) => set("teamCartUserId", value)}
      />

      {submitError && <Text style={{ color: colors.danger }}>{submitError}</Text>}
      {editable && <Button title={submitLabel} onPress={handleSubmit} disabled={submitting} />}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  content: { padding: 16, gap: 14, paddingBottom: 48 },
  notice: { fontSize: 14, fontStyle: "italic" },
  meta: { gap: 2 },
  metaNumber: { fontSize: 20, fontWeight: "700" },
  call: { flexDirection: "row", alignItems: "center", gap: 8, alignSelf: "flex-start" },
});
