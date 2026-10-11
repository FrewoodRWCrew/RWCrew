"use client";

// Ploeg Wizard step 4: which products must each of the team's kars carry,
// and how many? Pick one of the kars KarManagement assigned to the team
// (each button shows "loaded / needed"), then edit its list with exactly
// the same editor as StockMaster's "Benodigdheden" screen
// (components/module-4/kar-requirements-list.tsx): product search,
// quantity, comment, Excel template/upload, copy last season's list of the
// kar, Laadlijst PDF. Everything is stored in StockMaster's kar needs (no
// copy in this module), through Altsien Select's own endpoints, so a
// Kernlid needs no StockMaster rights. The wizard's Save / Complete step
// buttons store the open kar's list.

import { useCallback, useEffect, useMemo, useState } from "react";
import { useTranslations } from "next-intl";
import {
  altsienSelectLoadListPdfUrl,
  altsienSelectProductImageUrl,
  altsienSelectProductsTemplateUrl,
  getAltsienSelectPreviousRequirements,
  getAltsienSelectProductsCatalog,
  getAltsienSelectRequirements,
  getAltsienSelectWizard,
  importAltsienSelectProducts,
  listAltsienSelectProductsKars,
  saveAltsienSelectRequirements,
} from "@/lib/api";
import type { StockMasterKarSummary } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { KarRequirementsList, type KarRequirementsApi } from "@/components/module-4/kar-requirements-list";
import type { WizardStepProps } from "@/components/module-8/wizard/step-types";

export function ProductsStep({ teamId, seasonId, readOnly, onStateChange, registerSave }: WizardStepProps) {
  const t = useTranslations("altsienSelect.steps.products");
  const tReq = useTranslations("stockMaster.requirements");

  const [kars, setKars] = useState<StockMasterKarSummary[] | null>(null);
  const [loadFailed, setLoadFailed] = useState(false);
  const [karId, setKarId] = useState<number | null>(null);
  // Whether the open kar's list has unsaved changes (asked before switching kar).
  const [isDirty, setIsDirty] = useState(false);

  // The team's kars with their loading progress against this season's needs.
  const loadKars = useCallback(
    () =>
      listAltsienSelectProductsKars(teamId, seasonId)
        .then((result) => {
          setKars(result);
          setLoadFailed(false);
          return result;
        })
        .catch(() => {
          setLoadFailed(true);
          return [] as StockMasterKarSummary[];
        }),
    [teamId, seasonId],
  );

  useEffect(() => {
    loadKars().then((result) => {
      // A team with just one kar opens that kar's list straight away.
      if (result.length === 1) setKarId(result[0].kar_id);
    });
  }, [loadKars]);

  // The list's data, from this module's own endpoints for this team.
  const api = useMemo<KarRequirementsApi>(
    () => ({
      loadStock: () => getAltsienSelectProductsCatalog(teamId),
      loadRequirements: (season, kar) => getAltsienSelectRequirements(teamId, season, kar),
      loadPrevious: (season, kar) => getAltsienSelectPreviousRequirements(teamId, season, kar),
      save: (season, kar, lines) => saveAltsienSelectRequirements(teamId, season, kar, lines),
      importExcel: importAltsienSelectProducts,
      templateUrl: altsienSelectProductsTemplateUrl(),
      loadListPdfUrl: (kar, season, locale) => altsienSelectLoadListPdfUrl(teamId, kar, season, locale),
      productImageUrl: altsienSelectProductImageUrl,
    }),
    [teamId],
  );

  // After a save: refresh the kar buttons' progress and the wizard state
  // (emptying every list un-marks the step; the Ploegfiche data changes too).
  // Awaited by the list, so "Complete step" only runs on fresh data.
  const handleSaved = useCallback(async () => {
    const [state] = await Promise.all([getAltsienSelectWizard(teamId, seasonId), loadKars()]);
    onStateChange(state);
  }, [teamId, seasonId, loadKars, onStateChange]);

  if (loadFailed) {
    return <p className="text-sm text-destructive">{t("loadKarsFailed")}</p>;
  }
  if (kars === null) {
    return null;
  }
  if (kars.length === 0) {
    return <p className="text-sm text-muted-foreground">{t("noKars")}</p>;
  }

  const selectedKar = kars.find((kar) => kar.kar_id === karId) ?? null;

  return (
    <div className="flex flex-col gap-4">
      {/* One button per kar of the team, with "loaded / needed" once it has needs. */}
      <div className="flex flex-col gap-2">
        <Label>{t("chooseKar")}</Label>
        <div className="flex flex-wrap gap-2">
          {kars.map((kar) => (
            <Button
              key={kar.kar_id}
              variant={kar.kar_id === karId ? "default" : "outline"}
              onClick={() => {
                if (kar.kar_id === karId) return;
                if (isDirty && !window.confirm(tReq("discardChanges"))) return;
                setIsDirty(false);
                setKarId(kar.kar_id);
              }}
            >
              {kar.kar_nummer}
              {kar.required_total > 0 && (
                <span className="text-xs opacity-75">
                  {kar.loaded_toward_required}/{kar.required_total}
                </span>
              )}
            </Button>
          ))}
        </div>
      </div>

      {selectedKar ? (
        <KarRequirementsList
          // A fresh list per kar, so its saver never stores under another kar.
          key={selectedKar.kar_id}
          api={api}
          seasonId={seasonId}
          karId={selectedKar.kar_id}
          readOnly={readOnly}
          canCreate
          canEdit
          canDelete
          showSaveButton={false}
          onDirtyChange={setIsDirty}
          registerSave={registerSave}
          onSaved={handleSaved}
        />
      ) : (
        <p className="text-sm text-muted-foreground">{t("chooseKarHint")}</p>
      )}
    </div>
  );
}
