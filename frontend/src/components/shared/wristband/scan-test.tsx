"use client";

// The Test-scan screen of the Scans module, Atelier and Walkies: each passes
// its module key, so the module's own rights apply. The wristband company can
// only be connected from May 2027; until then (and to replay a real message
// later) this screen sends a scan message through exactly the same processing
// as the company's webhook — without its token — marked as a test. Two ways:
//   - "Formulier": fill in scanner, person, wristband number, team, ... and
//     the company's JSON is built (shown live);
//   - "JSON": paste a message or drop a .json file, sent as is.
// The result (status, matched team, whether a counter shows it) appears under
// the button, the message in the log below, and a "new" scan pops up live on
// the desk screen of that scanner when the team has reservations there.

import { useState } from "react";
import { FileJson, Send } from "lucide-react";
import { useTranslations } from "next-intl";
import { toast } from "sonner";
import { ApiError, wristbandTestApi } from "@/lib/api";
import type { WristbandScan, WristbandScanner, WristbandTestModule, WristbandTestScanResult } from "@/lib/types";
import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { SearchableSelect } from "@/components/ui/searchable-select";
import { Textarea } from "@/components/ui/textarea";
import { SCAN_STATUS_VARIANT, ScanLogTable } from "@/components/shared/wristband/scan-log-table";
import { useKeyedLoad } from "@/components/module-4/use-keyed-load";

type Tab = "form" | "json";

// The form's fields (all text, as typed).
interface FormValues {
  deviceId: string;
  deviceName: string;
  firstName: string;
  lastName: string;
  wristband: string;
  team: string;
  profile: string;
  email: string;
  size: string;
  event: string;
}

const EMPTY: FormValues = {
  deviceId: "14734",
  deviceName: "SUN0410",
  firstName: "",
  lastName: "",
  wristband: "",
  team: "",
  profile: "Vrijwilliger",
  email: "",
  size: "",
  event: "crew_participation",
};

/** The message the wristband company would send for these values (example format). */
function buildMessage(values: FormValues) {
  const person: Record<string, string> = { first_name: values.firstName.trim(), last_name: values.lastName.trim() };
  if (values.email.trim()) person.email = values.email.trim();
  if (values.size.trim()) person.size = values.size.trim();
  const deviceId = Number(values.deviceId);
  return {
    data: {
      association: values.team.trim(),
      attending_group: { id: "", name: values.team.trim() },
      device: { id: Number.isFinite(deviceId) && values.deviceId.trim() !== "" ? deviceId : values.deviceId.trim(), name: values.deviceName.trim(), uuid: "" },
      id: values.wristband.trim(),
      person,
      profile: { id: "", name: values.profile.trim() },
    },
    event: values.event.trim(),
    token: "test",
  };
}

interface ScanTestProps {
  moduleKey: WristbandTestModule;
  canSend: boolean;
  /** An extra line under the description (e.g. a module without a counter yet). */
  note?: string;
}

export function ScanTest({ moduleKey, canSend, note }: ScanTestProps) {
  const t = useTranslations("wristband.test");
  const tLog = useTranslations("wristband.log");
  const api = wristbandTestApi(moduleKey);
  const [tab, setTab] = useState<Tab>("form");
  const [values, setValues] = useState<FormValues>(EMPTY);
  const [json, setJson] = useState("");
  const [isDragging, setIsDragging] = useState(false);
  const [isSending, setIsSending] = useState(false);
  const [result, setResult] = useState<WristbandTestScanResult | null>(null);

  const scanners = useKeyedLoad<WristbandScanner[]>("test-scanners", api.listScanners);
  const teams = useKeyedLoad<{ id: number; name: string; active: boolean }[]>("test-teams", api.listTeams);
  const log = useKeyedLoad<WristbandScan[]>("test-scan-log", api.listLog);

  const preview = JSON.stringify(buildMessage(values), null, 2);

  function update(field: keyof FormValues, value: string) {
    setValues((current) => ({ ...current, [field]: value }));
  }

  // A dropped or chosen .json file becomes the JSON to send.
  async function readFile(file: File | undefined) {
    if (!file) return;
    setJson(await file.text());
    setTab("json");
  }

  async function send() {
    const raw = tab === "form" ? preview : json;
    setIsSending(true);
    try {
      const sent = await api.send(raw);
      setResult(sent);
      toast.success(t("sent"));
      log.reload();
      scanners.reload();
    } catch (error) {
      toast.error(error instanceof ApiError ? error.message : t("sendFailed"));
    } finally {
      setIsSending(false);
    }
  }

  const formReady = values.firstName.trim() !== "" && values.lastName.trim() !== "" && values.deviceId.trim() !== "";

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight underline">{t("title")}</h1>
        <p className="text-muted-foreground">{t("description")}</p>
        {note && <p className="mt-1 text-sm text-orange-700 dark:text-orange-300">{note}</p>}
      </div>

      <div className="flex gap-2">
        <Button variant={tab === "form" ? "default" : "outline"} onClick={() => setTab("form")}>
          {t("tabForm")}
        </Button>
        <Button variant={tab === "json" ? "default" : "outline"} onClick={() => setTab("json")}>
          <FileJson className="size-4" />
          {t("tabJson")}
        </Button>
      </div>

      {tab === "form" ? (
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
          <Card>
            <CardContent className="grid grid-cols-2 gap-4">
              {/* An existing scanner fills in its id and name; a new id registers a new scanner. */}
              <div className="col-span-2 flex flex-col gap-2">
                <Label>{t("existingScanner")}</Label>
                <SearchableSelect
                  value=""
                  onValueChange={(value) => {
                    const scanner = scanners.data?.find((item) => item.device_id === value);
                    if (scanner) setValues((current) => ({ ...current, deviceId: scanner.device_id, deviceName: scanner.device_name ?? "" }));
                  }}
                  disabled={(scanners.data ?? []).length === 0}
                  renderValue={() => t("pickScanner")}
                  options={(scanners.data ?? []).map((scanner) => ({
                    value: scanner.device_id,
                    label: scanner.label ? `${scanner.label} (${scanner.device_name ?? scanner.device_id})` : (scanner.device_name ?? scanner.device_id),
                  }))}
                />
              </div>
              <Field id="test-device-id" label={t("deviceId")} value={values.deviceId} onChange={(value) => update("deviceId", value)} required />
              <Field id="test-device-name" label={t("deviceName")} value={values.deviceName} onChange={(value) => update("deviceName", value)} />
              <Field id="test-first-name" label={t("firstName")} value={values.firstName} onChange={(value) => update("firstName", value)} required />
              <Field id="test-last-name" label={t("lastName")} value={values.lastName} onChange={(value) => update("lastName", value)} required />
              <Field id="test-wristband" label={t("wristband")} value={values.wristband} onChange={(value) => update("wristband", value)} />
              <div className="flex flex-col gap-2">
                <Label htmlFor="test-team">{t("team")}</Label>
                {/* A MasterData team, or any text to test a name that doesn't match. */}
                <Input id="test-team" list="test-team-options" value={values.team} onChange={(event) => update("team", event.target.value)} />
                <datalist id="test-team-options">
                  {(teams.data ?? []).map((team) => (
                    <option key={team.id} value={team.name} />
                  ))}
                </datalist>
              </div>
              <Field id="test-profile" label={t("profile")} value={values.profile} onChange={(value) => update("profile", value)} />
              <Field id="test-email" label={t("email")} value={values.email} onChange={(value) => update("email", value)} />
              <Field id="test-size" label={t("size")} value={values.size} onChange={(value) => update("size", value)} />
              <Field id="test-event" label={t("event")} value={values.event} onChange={(value) => update("event", value)} />
            </CardContent>
          </Card>
          <div className="flex flex-col gap-2">
            <Label>{t("preview")}</Label>
            <pre className="max-h-[60vh] overflow-auto rounded-md border bg-muted p-3 text-xs">{preview}</pre>
          </div>
        </div>
      ) : (
        <div
          onDragOver={(event) => {
            event.preventDefault();
            setIsDragging(true);
          }}
          onDragLeave={() => setIsDragging(false)}
          onDrop={(event) => {
            event.preventDefault();
            setIsDragging(false);
            void readFile(event.dataTransfer.files[0]);
          }}
          className={cn("flex flex-col gap-3 rounded-md border-2 border-dashed p-4", isDragging && "border-primary bg-primary/5")}
        >
          <p className="text-sm text-muted-foreground">{t("dropHint")}</p>
          <Input type="file" accept=".json,application/json" className="w-fit" onChange={(event) => void readFile(event.target.files?.[0])} />
          <Textarea rows={14} className="font-mono text-xs" placeholder={t("jsonPlaceholder")} value={json} onChange={(event) => setJson(event.target.value)} />
        </div>
      )}

      {canSend && (
        <div className="flex flex-wrap items-center gap-3">
          <Button size="lg" onClick={() => void send()} disabled={isSending || (tab === "form" ? !formReady : json.trim() === "")}>
            <Send className="size-4" />
            {t("send")}
          </Button>
          {result && (
            <span className="flex flex-wrap items-center gap-2 text-sm">
              <Badge variant={SCAN_STATUS_VARIANT[result.scan.status]}>{tLog(`statuses.${result.scan.status}`)}</Badge>
              {result.scan.status_detail && <span>{tLog(`details.${result.scan.status_detail}`)}</span>}
              {result.scan.status === "new" &&
                (result.team_name_matched
                  ? t("teamMatched", { team: result.team_name_matched })
                  : t("teamNotMatched"))}
              {result.scan.status === "new" &&
                (result.visible_at.length > 0 ? (
                  <span className="text-muted-foreground">{t("onDesk", { device: result.scan.device_id ?? "" })}</span>
                ) : (
                  <span className="text-orange-700 dark:text-orange-300">{t("notAtCounter")}</span>
                ))}
            </span>
          )}
        </div>
      )}

      <section className="flex flex-col gap-2">
        <h2 className="text-lg font-semibold">{tLog("logTitle")}</h2>
        <ScanLogTable scans={log.data ?? []} isLoading={log.isLoading} />
      </section>
    </div>
  );
}

/** A labelled text field of the form. */
function Field({
  id,
  label,
  value,
  onChange,
  required,
}: {
  id: string;
  label: string;
  value: string;
  onChange: (value: string) => void;
  required?: boolean;
}) {
  return (
    <div className="flex flex-col gap-2">
      <Label htmlFor={id}>
        {label}
        {required && <span className="text-destructive"> *</span>}
      </Label>
      <Input id={id} autoComplete="off" value={value} onChange={(event) => onChange(event.target.value)} />
    </div>
  );
}
