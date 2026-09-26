"use client";

// Ploeg Wizard step 1: at which festivals of the season is the team active?
// A checkbox per active festival (with its dates). Saved to
// MasterData_team_festival; deselecting a festival also clears the delivery
// location chosen for it in step 2.

import { useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import { toast } from "sonner";
import { ApiError, saveAltsienSelectFestivals } from "@/lib/api";
import { Checkbox } from "@/components/ui/checkbox";
import { Label } from "@/components/ui/label";
import { formatFestivalPeriod } from "@/components/module-8/wizard/format";
import type { WizardStepProps } from "@/components/module-8/wizard/step-types";

export function FestivalStep({ state, teamId, seasonId, readOnly, onStateChange, registerSave }: WizardStepProps) {
  const t = useTranslations("altsienSelect.steps.festivals");
  const savedIds = state.festivals.filter((festival) => festival.selected).map((festival) => festival.festival_id);
  const [draft, setDraft] = useState<Set<number>>(() => new Set(savedIds));

  const isDirty = draft.size !== savedIds.length || savedIds.some((id) => !draft.has(id));

  // Offer the wizard a saver for the pending selection.
  useEffect(() => {
    registerSave(async () => {
      if (!isDirty) return true;
      try {
        onStateChange(await saveAltsienSelectFestivals(teamId, seasonId, [...draft]));
        toast.success(t("saved"));
        return true;
      } catch (error) {
        toast.error(error instanceof ApiError ? error.message : t("saveFailed"));
        return false;
      }
    });
    return () => registerSave(null);
  });

  function toggle(festivalId: number, checked: boolean) {
    setDraft((current) => {
      const next = new Set(current);
      if (checked) next.add(festivalId);
      else next.delete(festivalId);
      return next;
    });
  }

  if (state.festivals.length === 0) {
    return <p className="text-sm text-muted-foreground">{t("noFestivals")}</p>;
  }

  return (
    <div className="flex flex-col gap-2">
      {state.festivals.map((festival) => (
        <Label
          key={festival.festival_id}
          htmlFor={`festival-${festival.festival_id}`}
          className="flex cursor-pointer items-center gap-3 rounded-md border p-3 font-normal hover:bg-muted/50 has-[[data-disabled]]:cursor-default"
        >
          <Checkbox
            id={`festival-${festival.festival_id}`}
            checked={draft.has(festival.festival_id)}
            disabled={readOnly}
            onCheckedChange={(checked) => toggle(festival.festival_id, checked === true)}
          />
          <span className="flex flex-1 flex-wrap items-baseline justify-between gap-x-4">
            <span className="font-medium">{festival.festival_name}</span>
            <span className="text-sm text-muted-foreground tabular-nums">
              {formatFestivalPeriod(festival.start_date, festival.end_date)}
            </span>
          </span>
        </Label>
      ))}
      {isDirty && !readOnly && <p className="text-xs text-muted-foreground">{t("unsaved")}</p>}
    </div>
  );
}
