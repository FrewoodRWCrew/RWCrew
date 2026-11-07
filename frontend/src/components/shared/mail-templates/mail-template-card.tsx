"use client";

// One editable mail text of an "Instellingen > E-mails" screen, shared by
// Atelier (module-5) and Altsien Select (module-8) so both look the same:
// subject, body and an on/off switch, the placeholders as buttons that insert
// themselves at the cursor, a live preview filled with example values, "Stuur
// test naar mij" and Opslaan. The texts are plain text with placeholders such
// as {voornaam}; a text with an unknown placeholder can't be saved.
//
// Each module passes its own save/test functions and its translation
// namespace (which holds the same keys: active, subject, body, placeholders.*,
// preview, changed, unsaved, save, saved, sendTest, testSent, errors.*).

import { useRef, useState } from "react";
import { Mail, Save } from "lucide-react";
import { useTranslations } from "next-intl";
import { toast } from "sonner";
import { ApiError } from "@/lib/api";
import { formatDateTimeNl } from "@/lib/date-time";
import type { MailTemplate } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";

// A placeholder in a text: a name between curly braces (as in the backend).
const PLACEHOLDER_PATTERN = /\{([^{}\s]*)\}/g;

/** The text with every known placeholder replaced by its example value. */
function fillExample(text: string, values: Record<string, string>): string {
  return text.replace(PLACEHOLDER_PATTERN, (match, name: string) => values[name] ?? match);
}

/** The placeholders in a text that don't exist (once each). */
function unknownPlaceholders(text: string, known: string[]): string[] {
  const names = [...text.matchAll(PLACEHOLDER_PATTERN)].map((match) => match[1]);
  return [...new Set(names.filter((name) => !known.includes(name)))];
}

/** The texts a save or a test sends. */
export interface MailTemplateInput {
  subject: string;
  body: string;
}

interface MailTemplateCardProps<T extends MailTemplate> {
  template: T;
  /** The card's heading and the line under it ("Sent after every …"). */
  title: string;
  help: string;
  placeholders: string[];
  exampleValues: Record<string, string>;
  canEdit: boolean;
  /** The module's translation namespace, e.g. "atelier.mailTemplates". */
  messagesNamespace: string;
  onSave: (input: MailTemplateInput & { active: boolean }) => Promise<T>;
  onTest: (input: MailTemplateInput) => Promise<{ sent_to: string }>;
  onSaved: (template: T) => void;
}

/** One mail: subject, body, on/off, placeholders, preview, save and test. */
export function MailTemplateCard<T extends MailTemplate>({
  template,
  title,
  help,
  placeholders,
  exampleValues,
  canEdit,
  messagesNamespace,
  onSave,
  onTest,
  onSaved,
}: MailTemplateCardProps<T>) {
  const t = useTranslations(messagesNamespace);
  const [subject, setSubject] = useState(template.subject);
  const [body, setBody] = useState(template.body);
  const [active, setActive] = useState(template.active);
  const [isBusy, setIsBusy] = useState(false);
  // Where a clicked placeholder goes: the field last focused (default the body).
  const [target, setTarget] = useState<"subject" | "body">("body");
  const subjectRef = useRef<HTMLInputElement>(null);
  const bodyRef = useRef<HTMLTextAreaElement>(null);

  const isDirty = subject !== template.subject || body !== template.body || active !== template.active;
  const unknown = unknownPlaceholders(`${subject}\n${body}`, placeholders);
  const isValid = subject.trim() !== "" && body.trim() !== "" && unknown.length === 0;
  const prefix = `mail-${template.key}`;

  // Insert a placeholder at the cursor of the field last used.
  function insert(name: string) {
    const element = target === "subject" ? subjectRef.current : bodyRef.current;
    const value = target === "subject" ? subject : body;
    const start = element?.selectionStart ?? value.length;
    const end = element?.selectionEnd ?? value.length;
    const next = `${value.slice(0, start)}{${name}}${value.slice(end)}`;
    if (target === "subject") setSubject(next);
    else setBody(next);
    // Put the cursor right after the inserted placeholder.
    const cursor = start + name.length + 2;
    window.requestAnimationFrame(() => {
      element?.focus();
      element?.setSelectionRange(cursor, cursor);
    });
  }

  // The backend's "code|param" errors, translated (else its message).
  function errorMessage(error: unknown): string {
    if (!(error instanceof ApiError)) return t("errors.generic");
    const [code, param] = error.message.split("|");
    return t.has(`errors.${code}`) ? t(`errors.${code}`, { p1: param ?? "" }) : error.message;
  }

  async function handleSave() {
    setIsBusy(true);
    try {
      const saved = await onSave({ subject, body, active });
      onSaved(saved);
      // The backend trims the texts: show what's stored.
      setSubject(saved.subject);
      setBody(saved.body);
      toast.success(t("saved"));
    } catch (error) {
      toast.error(errorMessage(error));
    } finally {
      setIsBusy(false);
    }
  }

  async function handleTest() {
    setIsBusy(true);
    try {
      const result = await onTest({ subject, body });
      toast.success(t("testSent", { email: result.sent_to }));
    } catch (error) {
      toast.error(errorMessage(error));
    } finally {
      setIsBusy(false);
    }
  }

  return (
    <Card>
      <CardContent className="flex flex-col gap-4">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h2 className="text-lg font-semibold">{title}</h2>
            <p className="text-sm text-muted-foreground">{help}</p>
          </div>
          <label className="flex items-center gap-2 text-sm font-medium">
            <Checkbox checked={active} onCheckedChange={(checked) => setActive(checked === true)} disabled={!canEdit} />
            {t("active")}
          </label>
        </div>

        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
          {/* The texts, with the placeholders to insert. */}
          <div className="flex flex-col gap-3">
            <div className="flex flex-col gap-2">
              <Label htmlFor={`${prefix}-subject`}>{t("subject")}</Label>
              <Input
                id={`${prefix}-subject`}
                ref={subjectRef}
                value={subject}
                maxLength={255}
                disabled={!canEdit}
                onFocus={() => setTarget("subject")}
                onChange={(event) => setSubject(event.target.value)}
              />
            </div>
            <div className="flex flex-col gap-2">
              <Label htmlFor={`${prefix}-body`}>{t("body")}</Label>
              <Textarea
                id={`${prefix}-body`}
                ref={bodyRef}
                rows={12}
                value={body}
                disabled={!canEdit}
                onFocus={() => setTarget("body")}
                onChange={(event) => setBody(event.target.value)}
              />
            </div>
            {canEdit && (
              <div className="flex flex-col gap-2">
                <p className="text-sm text-muted-foreground">{t("placeholdersHelp")}</p>
                <div className="flex flex-wrap gap-1.5">
                  {placeholders.map((name) => (
                    <Button
                      key={name}
                      type="button"
                      variant="outline"
                      size="sm"
                      className="font-mono"
                      title={t(`placeholders.${name}`)}
                      onClick={() => insert(name)}
                    >
                      {`{${name}}`}
                    </Button>
                  ))}
                </div>
              </div>
            )}
            {unknown.length > 0 && (
              <p className="text-sm text-destructive">{t("errors.unknown_placeholder", { p1: unknown.join(", ") })}</p>
            )}
          </div>

          {/* The mail as the receiver would get it, with example values. */}
          <div className="flex flex-col gap-2">
            <Label>{t("preview")}</Label>
            <div className="rounded-md border bg-muted/30 p-4 text-sm">
              <p className="mb-3 border-b pb-2 font-semibold">{fillExample(subject, exampleValues)}</p>
              <p className="whitespace-pre-wrap">{fillExample(body, exampleValues)}</p>
            </div>
          </div>
        </div>

        <div className="flex flex-wrap items-center justify-between gap-3">
          <span className="text-xs text-muted-foreground">
            {template.updated_at && t("changed", { when: formatDateTimeNl(template.updated_at), who: template.updated_by_name ?? "" })}
          </span>
          {canEdit && (
            <div className="flex items-center gap-3">
              {isDirty && <span className="text-sm text-muted-foreground">{t("unsaved")}</span>}
              <Button variant="outline" onClick={handleTest} disabled={isBusy || !isValid}>
                <Mail className="size-4" />
                {t("sendTest")}
              </Button>
              <Button onClick={handleSave} disabled={isBusy || !isDirty || !isValid}>
                <Save className="size-4" />
                {t("save")}
              </Button>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
