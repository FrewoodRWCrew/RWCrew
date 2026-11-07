"use client";

// Altsien Select's "Instellingen > E-mails" screen: the texts of the mails the
// module sends (today "Ploegfiche": the PDF a Kernlid can ask for once every
// wizard step is done) in the shared MailTemplateCard — same look as
// Atelier's — and the "In kopie (CC)" card: the addresses that get a copy of
// every Altsien Select mail. Saving needs "edit" on altsienselect.mailtemplates.

import { useState, type FormEvent } from "react";
import { Plus, Save, X } from "lucide-react";
import { useTranslations } from "next-intl";
import { toast } from "sonner";
import {
  ApiError,
  getAltsienSelectMailSettings,
  getAltsienSelectMailTemplates,
  saveAltsienSelectMailSettings,
  saveAltsienSelectMailTemplate,
  sendAltsienSelectTestMail,
} from "@/lib/api";
import { formatDateTimeNl } from "@/lib/date-time";
import type { AltsienSelectMailSettings, AltsienSelectMailTemplates } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { MailTemplateCard } from "@/components/shared/mail-templates/mail-template-card";
import { useKeyedLoad } from "@/components/module-4/use-keyed-load";

// A simple "looks like an email" check; the backend validates for real.
const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

interface MailSettingsScreenProps {
  canEdit: boolean;
}

export function MailSettingsScreen({ canEdit }: MailSettingsScreenProps) {
  const t = useTranslations("altsienSelect.mailTemplates");
  const templates = useKeyedLoad<AltsienSelectMailTemplates>("altsien-mail-templates", () =>
    getAltsienSelectMailTemplates(),
  );
  const mailSettings = useKeyedLoad<AltsienSelectMailSettings>("altsien-mail-settings", () =>
    getAltsienSelectMailSettings(),
  );

  return (
    <div className="flex flex-col gap-4">
      <div>
        <h1 className="text-2xl font-bold tracking-tight underline">{t("title")}</h1>
        <p className="text-muted-foreground">{t("description")}</p>
      </div>
      {(templates.isLoading || mailSettings.isLoading) && (
        <p className="text-sm text-muted-foreground">{t("loading")}</p>
      )}

      {mailSettings.data && (
        <CcCard
          key={mailSettings.data.updated_at ?? "new"}
          settings={mailSettings.data}
          canEdit={canEdit}
          onSaved={mailSettings.setData}
        />
      )}

      {templates.data?.templates.map((template) => (
        <MailTemplateCard
          key={template.key}
          template={template}
          title={t(`kinds.${template.key}.title`)}
          help={t(`kinds.${template.key}.help`)}
          placeholders={templates.data!.placeholders}
          exampleValues={templates.data!.example_values}
          canEdit={canEdit}
          messagesNamespace="altsienSelect.mailTemplates"
          onSave={(input) => saveAltsienSelectMailTemplate(template.key, input)}
          onTest={(input) => sendAltsienSelectTestMail(template.key, input)}
          onSaved={(saved) =>
            templates.setData({
              ...templates.data!,
              templates: templates.data!.templates.map((item) => (item.key === saved.key ? saved : item)),
            })
          }
        />
      ))}
    </div>
  );
}

interface CcCardProps {
  settings: AltsienSelectMailSettings;
  canEdit: boolean;
  onSaved: (settings: AltsienSelectMailSettings) => void;
}

/** The CC list: type an address + Enter (or "+") to add it, × to remove, Opslaan. */
function CcCard({ settings, canEdit, onSaved }: CcCardProps) {
  const t = useTranslations("altsienSelect.mailTemplates.cc");
  const tErrors = useTranslations("altsienSelect.mailTemplates.errors");
  const [addresses, setAddresses] = useState<string[]>(settings.cc_addresses);
  const [draft, setDraft] = useState("");
  const [isBusy, setIsBusy] = useState(false);

  const isDirty =
    addresses.length !== settings.cc_addresses.length ||
    addresses.some((address, index) => address !== settings.cc_addresses[index]);

  // Add the typed address (lowercase, once) after a format check.
  function handleAdd(event?: FormEvent) {
    event?.preventDefault();
    const address = draft.trim().toLowerCase();
    if (!address) return;
    if (!EMAIL_PATTERN.test(address)) {
      toast.error(t("invalid", { email: address }));
      return;
    }
    if (!addresses.includes(address)) setAddresses([...addresses, address]);
    setDraft("");
  }

  async function handleSave() {
    setIsBusy(true);
    try {
      onSaved(await saveAltsienSelectMailSettings(addresses));
      toast.success(t("saved"));
    } catch (error) {
      toast.error(error instanceof ApiError && error.status !== 422 ? error.message : tErrors("generic"));
    } finally {
      setIsBusy(false);
    }
  }

  return (
    <Card>
      <CardContent className="flex flex-col gap-4">
        <div>
          <h2 className="text-lg font-semibold">{t("title")}</h2>
          <p className="text-sm text-muted-foreground">{t("help")}</p>
        </div>

        {/* The current list as removable chips. */}
        <div className="flex flex-wrap gap-2">
          {addresses.length === 0 && <span className="text-sm text-muted-foreground">{t("empty")}</span>}
          {addresses.map((address) => (
            <span
              key={address}
              className="inline-flex items-center gap-1 rounded-full border bg-muted/50 py-1 pr-1 pl-3 text-sm"
            >
              {address}
              {canEdit && (
                <button
                  type="button"
                  className="rounded-full p-0.5 text-muted-foreground hover:bg-muted hover:text-foreground"
                  aria-label={t("remove", { email: address })}
                  onClick={() => setAddresses(addresses.filter((item) => item !== address))}
                >
                  <X className="size-3.5" />
                </button>
              )}
            </span>
          ))}
        </div>

        {canEdit && (
          <form onSubmit={handleAdd} className="flex max-w-xl flex-col gap-2">
            <Label htmlFor="altsien-cc-new">{t("add")}</Label>
            <div className="flex gap-2">
              <Input
                id="altsien-cc-new"
                type="email"
                value={draft}
                placeholder="naam@voorbeeld.be"
                onChange={(event) => setDraft(event.target.value)}
              />
              <Button type="submit" variant="outline" disabled={!draft.trim()}>
                <Plus className="size-4" />
                {t("addButton")}
              </Button>
            </div>
          </form>
        )}

        <div className="flex flex-wrap items-center justify-between gap-3">
          <span className="text-xs text-muted-foreground">
            {settings.updated_at &&
              t("changed", { when: formatDateTimeNl(settings.updated_at), who: settings.updated_by_name ?? "" })}
          </span>
          {canEdit && (
            <div className="flex items-center gap-3">
              {isDirty && <span className="text-sm text-muted-foreground">{t("unsaved")}</span>}
              <Button onClick={handleSave} disabled={isBusy || !isDirty}>
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
