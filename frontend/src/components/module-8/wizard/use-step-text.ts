"use client";

// A wizard step's translated title and description
// ("altsienSelect.steps.<key>.title/.description"). A step that was added in
// the backend but has no translation yet falls back to the backend's own
// English label, so it still shows up sensibly.

import { useTranslations } from "next-intl";

export function useStepText() {
  const t = useTranslations("altsienSelect.steps");
  return (step: { key: string; label: string }) => ({
    title: t.has(`${step.key}.title`) ? t(`${step.key}.title`) : step.label,
    description: t.has(`${step.key}.description`) ? t(`${step.key}.description`) : "",
  });
}
