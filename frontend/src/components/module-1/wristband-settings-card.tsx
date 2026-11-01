"use client";

// The Wristbands card on the Scans module's Settings screen: the webhook
// address, the token the wristband company sends (generated here, one per
// environment; the key is only shown once, right after generating), the
// folder with the JSON files, and a link to the explanation PDF that can be
// forwarded to the company. Replacing or revoking a token stops the old one
// immediately, so both ask for confirmation first.

import { useState } from "react";
import { FileText, KeyRound } from "lucide-react";
import { useLocale, useTranslations } from "next-intl";
import { toast } from "sonner";
import {
  ApiError,
  generateWristbandToken,
  getWristbandSettings,
  moduleHelpPdfUrl,
  revokeWristbandToken,
} from "@/lib/api";
import { API_BASE_URL } from "@/lib/config";
import { formatDateTime } from "@/lib/date-time";
import type { WristbandSettings } from "@/lib/types";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { copyToClipboard } from "@/components/module-1/copy-to-clipboard";

interface WristbandSettingsCardProps {
  initialSettings: WristbandSettings;
  canEdit: boolean;
}

export function WristbandSettingsCard({ initialSettings, canEdit }: WristbandSettingsCardProps) {
  const t = useTranslations("wristband.settings");
  const tCommon = useTranslations("common");
  const locale = useLocale();
  const [settings, setSettings] = useState(initialSettings);
  const [isBusy, setIsBusy] = useState(false);
  // Which action waits for confirmation.
  const [confirming, setConfirming] = useState<"replace" | "revoke" | null>(null);
  // The key just generated: only in memory, gone when the dialog closes.
  const [newToken, setNewToken] = useState<string | null>(null);

  const isSet = settings.webhook_token_configured;

  async function generate() {
    setIsBusy(true);
    try {
      const { token } = await generateWristbandToken();
      setNewToken(token);
      setSettings(await getWristbandSettings());
    } catch (error) {
      toast.error(error instanceof ApiError ? error.message : t("tokenFailed"));
    } finally {
      setIsBusy(false);
      setConfirming(null);
    }
  }

  async function revoke() {
    setIsBusy(true);
    try {
      await revokeWristbandToken();
      setSettings(await getWristbandSettings());
      toast.success(t("tokenRevoked"));
    } catch (error) {
      toast.error(error instanceof ApiError ? error.message : t("tokenFailed"));
    } finally {
      setIsBusy(false);
      setConfirming(null);
    }
  }

  return (
    <div className="flex max-w-2xl flex-col gap-2 rounded-md border p-4">
      <Label className="text-base font-bold underline">{t("webhookTitle")}</Label>
      <p className="text-sm text-muted-foreground">{t("webhookDescription")}</p>
      <Input readOnly value={`${API_BASE_URL}${settings.webhook_path}`} className="font-mono text-sm" />

      <p className={isSet ? "text-sm text-muted-foreground" : "text-sm text-destructive"}>
        {isSet ? t("tokenConfigured") : t("tokenMissing")}
      </p>
      {isSet && settings.webhook_token_generated_at && (
        <p className="text-sm text-muted-foreground">
          {t("tokenGeneratedAt", { when: formatDateTime(settings.webhook_token_generated_at) })}{" "}
          {settings.webhook_token_last_used_at
            ? t("tokenLastUsed", { when: formatDateTime(settings.webhook_token_last_used_at) })
            : t("tokenNeverUsed")}
        </p>
      )}

      {canEdit && (
        <div className="flex flex-wrap gap-2">
          <Button
            type="button"
            variant="outline"
            disabled={isBusy}
            onClick={() => (isSet ? setConfirming("replace") : void generate())}
          >
            <KeyRound className="size-4" />
            {isSet ? t("tokenReplace") : t("tokenGenerate")}
          </Button>
          {isSet && (
            <Button type="button" variant="outline" disabled={isBusy} onClick={() => setConfirming("revoke")}>
              {t("tokenRevoke")}
            </Button>
          )}
        </div>
      )}

      <a
        href={moduleHelpPdfUrl("module-1", locale, "wristband-integration")}
        target="_blank"
        rel="noopener noreferrer"
        className="inline-flex w-fit items-center gap-1.5 text-sm font-medium underline"
      >
        <FileText className="size-4" />
        {t("integrationLink")}
      </a>
      <p className="text-sm text-muted-foreground">{t("integrationHint")}</p>

      <p className="text-sm text-muted-foreground">{t("sourceFolder", { folder: settings.source_folder })}</p>

      <AlertDialog open={confirming !== null} onOpenChange={(open) => !open && setConfirming(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>{confirming === "revoke" ? t("revokeConfirmTitle") : t("replaceConfirmTitle")}</AlertDialogTitle>
            <AlertDialogDescription>
              {confirming === "revoke" ? t("revokeConfirmDescription") : t("replaceConfirmDescription")}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>{tCommon("cancel")}</AlertDialogCancel>
            <AlertDialogAction
              variant="destructive"
              disabled={isBusy}
              onClick={() => void (confirming === "revoke" ? revoke() : generate())}
            >
              {confirming === "revoke" ? t("tokenRevoke") : t("tokenReplace")}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      <Dialog open={newToken !== null} onOpenChange={(open) => !open && setNewToken(null)}>
        <DialogContent className="sm:max-w-xl">
          <DialogHeader>
            <DialogTitle>{t("newTokenTitle")}</DialogTitle>
            <DialogDescription>{t("newTokenDescription")}</DialogDescription>
          </DialogHeader>
          <div className="flex gap-2">
            <Input readOnly value={newToken ?? ""} className="font-mono text-sm" />
            <Button
              type="button"
              variant="outline"
              onClick={() =>
                copyToClipboard(
                  newToken ?? "",
                  () => toast.success(t("copied")),
                  () => toast.error(t("copyFailed")),
                )
              }
            >
              {t("copy")}
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
