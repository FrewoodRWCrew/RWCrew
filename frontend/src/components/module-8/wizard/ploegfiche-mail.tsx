"use client";

// The Ploegfiche PDF by mail: once every step of a team's wizard is done, the
// Kernlid can get the PDF with everything confirmed in their own mailbox (the
// module's CC list gets a copy, see backend module_8/notifications.py).
// usePloegficheMail gives the wizard a "send" function with its busy state;
// PloegficheMailDialog is the question asked right after the last open step is
// completed, PloegficheMailButton the "Mail PDF" button in the all-done banner.

import { useState } from "react";
import { Mail } from "lucide-react";
import { useLocale, useTranslations } from "next-intl";
import { toast } from "sonner";
import { ApiError, mailAltsienSelectPloegfiche } from "@/lib/api";
import { Button } from "@/components/ui/button";
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

/** Send the team's Ploegfiche to yourself; true when the backend accepted it. */
export function usePloegficheMail(teamId: number, seasonId: number) {
  const t = useTranslations("altsienSelect.wizard.ploegficheMail");
  const locale = useLocale();
  const [isSending, setIsSending] = useState(false);

  async function send(): Promise<boolean> {
    setIsSending(true);
    try {
      const result = await mailAltsienSelectPloegfiche(teamId, seasonId, locale);
      toast.success(t("sent", { email: result.sent_to }));
      return true;
    } catch (error) {
      // The backend's codes ("steps_not_done", ...) are translated; else its message.
      const code = error instanceof ApiError ? error.message : "";
      toast.error(t.has(`errors.${code}`) ? t(`errors.${code}`) : code || t("errors.generic"));
      return false;
    } finally {
      setIsSending(false);
    }
  }

  return { send, isSending };
}

interface PloegficheMailDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  isSending: boolean;
  onSend: () => Promise<boolean>;
}

/** "All steps are done — do you want the PDF by mail?" */
export function PloegficheMailDialog({ open, onOpenChange, isSending, onSend }: PloegficheMailDialogProps) {
  const t = useTranslations("altsienSelect.wizard.ploegficheMail");

  async function handleYes() {
    if (await onSend()) onOpenChange(false);
  }

  return (
    <AlertDialog open={open} onOpenChange={onOpenChange}>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>{t("askTitle")}</AlertDialogTitle>
          <AlertDialogDescription>{t("askDescription")}</AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel disabled={isSending}>{t("no")}</AlertDialogCancel>
          <AlertDialogAction disabled={isSending} onClick={handleYes}>
            <Mail className="size-4" />
            {t("yes")}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}

interface PloegficheMailButtonProps {
  isSending: boolean;
  onSend: () => Promise<boolean>;
}

/** "Mail PDF": send the Ploegfiche again later. */
export function PloegficheMailButton({ isSending, onSend }: PloegficheMailButtonProps) {
  const t = useTranslations("altsienSelect.wizard.ploegficheMail");
  return (
    <Button variant="outline" size="sm" disabled={isSending} onClick={() => void onSend()}>
      <Mail className="size-4" />
      {t("button")}
    </Button>
  );
}
