// A Ploeg Wizard step whose real content will come from a module that
// doesn't exist yet (products, walkie-talkies) — and the fallback for any
// step key that has no component registered yet (see ./index.ts). It only
// explains that; the wizard's own "Complete step" button still works, so
// the flow can be walked through end to end already.

import { Construction } from "lucide-react";
import { useTranslations } from "next-intl";

// Takes no props: it shows the same note for every step and team.
export function PlaceholderStep() {
  const t = useTranslations("altsienSelect.wizard");
  return (
    <div className="flex items-start gap-3 rounded-md border border-dashed p-4 text-sm text-muted-foreground">
      <Construction className="mt-0.5 size-5 shrink-0" aria-hidden="true" />
      <p>{t("placeholderText")}</p>
    </div>
  );
}
