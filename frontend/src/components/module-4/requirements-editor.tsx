"use client";

// StockMaster's "Benodigdheden": what each team needs in which kar, per
// season. Pick a team, then one of its kars, and edit the product list with
// the same basket-style input as the booking panel (search, Enter,
// quantity, Enter). "Kopieer van vorig seizoen" offers last season's list of
// the same kar line by line (only adds/updates, never removes). Saving
// stores the list under the logged-in user. These needs pre-fill "Kar
// laden", show as loading progress on the kar cards and feed "Te bestellen".
// The list itself is KarRequirementsList, shared with Altsien Select's
// Products wizard step; this screen adds the season, team and kar pickers.

import { useCallback, useEffect, useMemo, useState } from "react";
import { useTranslations } from "next-intl";
import { useSearchParams } from "next/navigation";
import { toast } from "sonner";
import {
  getStockMasterPreviousRequirements,
  getStockMasterRequirements,
  getStockMasterStock,
  importStockMasterBookIn,
  listStockMasterKars,
  saveStockMasterRequirements,
  stockMasterBookInTemplateUrl,
  stockMasterLoadListPdfUrl,
  stockMasterProductImageUrl,
} from "@/lib/api";
import type { Season, StockMasterKarSummary, StockMasterMyPermissions } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { KarRequirementsList, type KarRequirementsApi } from "@/components/module-4/kar-requirements-list";
import { StockMasterSeasonSelect, useStockMasterSeasonId } from "@/components/module-4/stockmaster-season-select";
import { hasRight } from "@/components/module-4/stockmaster-common";

interface RequirementsEditorProps {
  seasons: Season[];
  permissions: StockMasterMyPermissions;
}

const NO_TEAM = "none";

/** The list's data, from StockMaster's own endpoints. */
const STOCKMASTER_REQUIREMENTS_API: KarRequirementsApi = {
  loadStock: getStockMasterStock,
  loadRequirements: getStockMasterRequirements,
  loadPrevious: getStockMasterPreviousRequirements,
  save: saveStockMasterRequirements,
  importExcel: importStockMasterBookIn,
  templateUrl: stockMasterBookInTemplateUrl(),
  loadListPdfUrl: stockMasterLoadListPdfUrl,
  productImageUrl: stockMasterProductImageUrl,
};

export function RequirementsEditor({ seasons, permissions }: RequirementsEditorProps) {
  const t = useTranslations("stockMaster");
  const tReq = useTranslations("stockMaster.requirements");
  const searchParams = useSearchParams();
  const seasonId = useStockMasterSeasonId(seasons);
  const season = seasons.find((item) => item.id === seasonId) ?? null;

  const canCreate = hasRight(permissions, "requirements", "create");
  const canEdit = hasRight(permissions, "requirements", "edit");
  const canDelete = hasRight(permissions, "requirements", "delete");
  const seasonLocked =
    season !== null && !season.periode_open && !permissions.editable_screen_keys.includes("stockmaster.closedseason");

  const [kars, setKars] = useState<StockMasterKarSummary[]>([]);
  const [teamName, setTeamName] = useState<string | null>(null);
  const [karId, setKarId] = useState<number | null>(() => Number(searchParams.get("kar")) || null);
  // Whether the open kar's list has unsaved changes (asked before switching kar).
  const [isDirty, setIsDirty] = useState(false);

  // The kar cards (with their loading progress) of the season.
  const loadKars = useCallback(
    () =>
      listStockMasterKars(seasonId)
        .then((result) => {
          setKars(result);
          return result;
        })
        .catch(() => {
          toast.error(t("errors.loadFailed"));
          return [] as StockMasterKarSummary[];
        }),
    [seasonId, t],
  );

  useEffect(() => {
    loadKars().then((result) => {
      // A kar passed in the URL also picks its team.
      const fromUrl = result.find((kar) => kar.kar_id === karId);
      if (fromUrl) setTeamName(fromUrl.team_name ?? NO_TEAM);
    });
    // Only on a season change.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [loadKars]);

  const teams = useMemo(() => {
    const names = new Set(kars.map((kar) => kar.team_name ?? NO_TEAM));
    return [...names].sort((a, b) => (a === NO_TEAM ? 1 : b === NO_TEAM ? -1 : a.localeCompare(b)));
  }, [kars]);
  const teamKars = kars.filter((kar) => (kar.team_name ?? NO_TEAM) === teamName);
  const selectedKar = kars.find((kar) => kar.kar_id === karId) ?? null;

  const readOnly = seasonLocked || (!canCreate && !canEdit && !canDelete);
  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight underline">{tReq("title")}</h1>
          <p className="text-muted-foreground">{tReq("description")}</p>
        </div>
        <StockMasterSeasonSelect seasons={seasons} seasonId={seasonId} />
      </div>

      {seasonLocked && <p className="rounded-md bg-destructive/10 px-3 py-2 text-sm text-destructive">{t("errors.season_closed")}</p>}

      <div className="flex flex-wrap items-end gap-4">
        <div className="flex w-64 flex-col gap-2">
          <Label htmlFor="req-team">{t("common.team")}</Label>
          <Select
            value={teamName ?? ""}
            onValueChange={(value) => {
              setTeamName(value || null);
              // A team with just one kar opens that kar's list straight away.
              const karsOfTeam = kars.filter((kar) => (kar.team_name ?? NO_TEAM) === value);
              setKarId(karsOfTeam.length === 1 ? karsOfTeam[0].kar_id : null);
            }}
          >
            <SelectTrigger id="req-team" className="w-full">
              <SelectValue>
                {(value: string | null) => (!value ? tReq("chooseTeam") : value === NO_TEAM ? t("common.noTeam") : value)}
              </SelectValue>
            </SelectTrigger>
            <SelectContent>
              {teams.map((name) => (
                <SelectItem key={name} value={name}>
                  {name === NO_TEAM ? t("common.noTeam") : name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        {teamName !== null && (
          <div className="flex flex-col gap-2">
            <Label>{tReq("chooseKar")}</Label>
            <div className="flex flex-wrap gap-2">
              {teamKars.map((kar) => (
                <Button
                  key={kar.kar_id}
                  variant={kar.kar_id === karId ? "default" : "outline"}
                  onClick={() => {
                    if (isDirty && !window.confirm(tReq("discardChanges"))) return;
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
        )}
      </div>

      {selectedKar && seasonId !== null && (
        <KarRequirementsList
          api={STOCKMASTER_REQUIREMENTS_API}
          seasonId={seasonId}
          karId={selectedKar.kar_id}
          readOnly={readOnly}
          canCreate={canCreate}
          canEdit={canEdit}
          canDelete={canDelete}
          onDirtyChange={setIsDirty}
          onSaved={async () => {
            await loadKars();
          }}
        />
      )}
    </div>
  );
}
