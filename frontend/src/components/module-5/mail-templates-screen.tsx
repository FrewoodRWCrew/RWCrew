"use client";

// Atelier's "Instellingen > E-mails" screen: the two mails a person gets
// after a transaction at the counter desk — "Uitgifte" after Ophalen and
// "Inname" after Terugbrengen — each with its own subject, body and on/off
// switch. The card itself (placeholders, preview, test mail, save) is the
// shared MailTemplateCard, also used by Altsien Select.

import { useTranslations } from "next-intl";
import { getAtelierMailTemplates, saveAtelierMailTemplate, sendAtelierTestMail } from "@/lib/api";
import type { AtelierMailTemplateKey, AtelierMailTemplates } from "@/lib/types";
import { MailTemplateCard } from "@/components/shared/mail-templates/mail-template-card";
import { useKeyedLoad } from "@/components/module-4/use-keyed-load";

interface MailTemplatesScreenProps {
  canEdit: boolean;
}

export function MailTemplatesScreen({ canEdit }: MailTemplatesScreenProps) {
  const t = useTranslations("atelier.mailTemplates");
  const data = useKeyedLoad<AtelierMailTemplates>("mail-templates", () => getAtelierMailTemplates());

  return (
    <div className="flex flex-col gap-4">
      <div>
        <h1 className="text-2xl font-bold tracking-tight underline">{t("title")}</h1>
        <p className="text-muted-foreground">{t("description")}</p>
      </div>
      {data.isLoading && <p className="text-sm text-muted-foreground">{t("loading")}</p>}
      {data.data?.templates.map((template) => {
        const key = template.key as AtelierMailTemplateKey;
        return (
          <MailTemplateCard
            key={key}
            template={template}
            title={t(`kinds.${key}.title`)}
            help={t(`kinds.${key}.help`)}
            placeholders={data.data!.placeholders}
            exampleValues={data.data!.example_values}
            canEdit={canEdit}
            messagesNamespace="atelier.mailTemplates"
            onSave={(input) => saveAtelierMailTemplate(key, input)}
            onTest={(input) => sendAtelierTestMail(key, input)}
            onSaved={(saved) =>
              data.setData({
                ...data.data!,
                templates: data.data!.templates.map((item) => (item.key === saved.key ? saved : item)),
              })
            }
          />
        );
      })}
    </div>
  );
}
