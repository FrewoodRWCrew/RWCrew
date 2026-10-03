"use client";

// The phone-app link on the install page (module-10), shown read-only with a
// "Copy" button, so it can be pasted into a chat or mail to someone's phone.

import { useTranslations } from "next-intl";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

interface CopyInstallLinkProps {
  installUrl: string;
}

export function CopyInstallLink({ installUrl }: CopyInstallLinkProps) {
  const t = useTranslations("mobileApp");

  async function handleCopy() {
    // The clipboard API can be refused (e.g. on plain http), so say so instead of failing silently.
    try {
      await navigator.clipboard.writeText(installUrl);
      toast.success(t("linkCopied"));
    } catch {
      toast.error(t("linkCopyFailed"));
    }
  }

  return (
    <div className="flex gap-2">
      <Input readOnly value={installUrl} aria-label={t("linkLabel")} onFocus={(event) => event.target.select()} />
      <Button type="button" variant="outline" onClick={handleCopy}>
        {t("copyLink")}
      </Button>
    </div>
  );
}
