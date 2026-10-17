"use client";

// Kar laden's first screen, the loading overview: every kar with needs this
// season (or every kar, with "Toon alle karren"), each with how many of its
// needed product types are fully loaded (progress bar) and how many pieces,
// a "Laden" button that opens the booking screen for that kar
// (?kar=<id>, see kar-load-screen.tsx), and a doc icon for its Laadlijst.
// Ticking kars prints their Laadlijsten as one PDF. Typing a kar number and
// pressing Enter opens it too. Follows the app's list-screen table pattern
// (pinned header and Actions column, capped scroll box).

import { useEffect, useState } from "react";
import { FileText, Play } from "lucide-react";
import { useLocale, useTranslations } from "next-intl";
import { toast } from "sonner";
import { useRouter } from "@/i18n/navigation";
import { listStockMasterKars, stockMasterLoadListPdfUrl, stockMasterLoadListsPdfUrl } from "@/lib/api";
import type { Season, StockMasterKarSummary, StockMasterMyPermissions } from "@/lib/types";
import { Button, buttonVariants } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { ProcessFlow } from "@/components/module-4/process-flow";
import { KarStatusBadge } from "@/components/module-4/stock-pickers";
import { StockMasterSeasonSelect, useStockMasterSeasonId } from "@/components/module-4/stockmaster-season-select";
import {
  ACTION_PATHS,
  STOCKMASTER_BASE,
  readRemembered,
  remember,
} from "@/components/module-4/stockmaster-common";

interface KarLoadOverviewProps {
  seasons: Season[];
  permissions: StockMasterMyPermissions;
}

export function KarLoadOverview({ seasons, permissions }: KarLoadOverviewProps) {
  const t = useTranslations("stockMaster");
  const tOverview = useTranslations("stockMaster.karLoadOverview");
  const locale = useLocale();
  const router = useRouter();
  const seasonId = useStockMasterSeasonId(seasons);
  const [kars, setKars] = useState<StockMasterKarSummary[] | null>(null);
  const [search, setSearch] = useState("");
  const [showAll, setShowAll] = useState<boolean>(() => readRemembered("karLoadShowAll", false));
  const [checked, setChecked] = useState<Set<number>>(new Set());

  useEffect(() => {
    listStockMasterKars(seasonId)
      .then(setKars)
      .catch(() => toast.error(t("errors.loadFailed")));
  }, [seasonId, t]);

  // Kars with needs this season (unless every kar is asked for), matching the search.
  const needle = search.trim().toLowerCase();
  const visible = (kars ?? []).filter(
    (kar) =>
      (showAll || kar.required_product_count > 0) &&
      (!needle || kar.kar_nummer.toLowerCase().includes(needle) || (kar.team_name ?? "").toLowerCase().includes(needle)),
  );
  // Only ticked kars that are still in the list count (the filters can hide some).
  const selectedIds = visible.filter((kar) => checked.has(kar.kar_id)).map((kar) => kar.kar_id);
  const allChecked = visible.length > 0 && selectedIds.length === visible.length;

  /** Open the booking screen for one kar. */
  function openKar(kar: StockMasterKarSummary) {
    router.push(`${STOCKMASTER_BASE}${ACTION_PATHS.kar_load}?kar=${kar.kar_id}${seasonId ? `&season=${seasonId}` : ""}`);
  }

  // Enter on an exact kar number (or the only match) opens that kar.
  function handleSearchKey(event: React.KeyboardEvent<HTMLInputElement>) {
    if (event.key !== "Enter") return;
    const exact = visible.find((kar) => kar.kar_nummer.toLowerCase() === needle);
    const target = exact ?? (visible.length === 1 ? visible[0] : null);
    if (target) openKar(target);
  }

  function toggle(karId: number, on: boolean) {
    setChecked((current) => {
      const next = new Set(current);
      if (on) next.add(karId);
      else next.delete(karId);
      return next;
    });
  }

  function toggleAll(on: boolean) {
    setChecked(on ? new Set(visible.map((kar) => kar.kar_id)) : new Set());
  }

  return (
    <div className="flex flex-col gap-6">
      <ProcessFlow action="kar_load" permissions={permissions} />

      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight underline">{t("actions.kar_load.title")}</h1>
          <p className="text-muted-foreground">{tOverview("description")}</p>
        </div>
        <StockMasterSeasonSelect seasons={seasons} seasonId={seasonId} />
      </div>

      {/* Search, "show all kars" and printing the ticked kars' Laadlijsten. */}
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div className="flex flex-wrap items-end gap-4">
          <div className="flex w-64 flex-col gap-2">
            <Label htmlFor="kar-load-search">{t("common.search")}</Label>
            <Input
              id="kar-load-search"
              autoFocus
              placeholder={t("common.karSearchPlaceholder")}
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              onKeyDown={handleSearchKey}
            />
          </div>
          <div className="flex h-8 items-center gap-2">
            <Checkbox
              id="kar-load-show-all"
              checked={showAll}
              onCheckedChange={(value) => {
                setShowAll(value);
                remember("karLoadShowAll", value);
              }}
            />
            <Label htmlFor="kar-load-show-all">{tOverview("showAll")}</Label>
          </div>
        </div>
        {selectedIds.length > 0 && seasonId !== null ? (
          <a
            href={stockMasterLoadListsPdfUrl(selectedIds, seasonId, locale)}
            target="_blank"
            rel="noreferrer"
            className={buttonVariants({ variant: "outline", size: "sm" })}
          >
            <FileText />
            {tOverview("printSelected", { count: selectedIds.length })}
          </a>
        ) : (
          <Button variant="outline" size="sm" disabled>
            <FileText />
            {tOverview("printSelected", { count: 0 })}
          </Button>
        )}
      </div>

      {kars === null && <p className="text-sm text-muted-foreground">{t("common.loading")}</p>}
      {kars !== null && visible.length === 0 && <p className="text-sm text-muted-foreground">{tOverview("empty")}</p>}

      {visible.length > 0 && (
        <div className="rounded-md border [&>div]:max-h-[65vh] [&>div]:overflow-y-auto">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="sticky top-0 z-20 w-10 bg-background">
                  <Checkbox
                    checked={allChecked}
                    indeterminate={selectedIds.length > 0 && !allChecked}
                    onCheckedChange={(value) => toggleAll(value)}
                    aria-label={tOverview("selectAll")}
                  />
                </TableHead>
                <TableHead className="sticky top-0 z-20 bg-background font-bold underline">{tOverview("columnKar")}</TableHead>
                <TableHead className="sticky top-0 z-20 bg-background font-bold underline">
                  {tOverview("columnProducts")}
                </TableHead>
                <TableHead className="sticky top-0 z-20 bg-background font-bold underline">
                  {tOverview("columnPieces")}
                </TableHead>
                <TableHead className="sticky top-0 right-0 z-30 bg-background text-right font-bold underline">
                  {tOverview("columnActions")}
                </TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {visible.map((kar) => {
                const hasNeeds = kar.required_product_count > 0;
                const complete = hasNeeds && kar.loaded_product_count >= kar.required_product_count;
                const percent = hasNeeds
                  ? Math.round((kar.loaded_product_count / kar.required_product_count) * 100)
                  : 0;
                return (
                  <TableRow key={kar.kar_id} className="group">
                    <TableCell>
                      <Checkbox
                        checked={checked.has(kar.kar_id)}
                        onCheckedChange={(value) => toggle(kar.kar_id, value)}
                        aria-label={kar.kar_nummer}
                      />
                    </TableCell>
                    <TableCell>
                      <div className="font-medium">{kar.kar_nummer}</div>
                      <div className="text-xs text-muted-foreground">{kar.team_name ?? t("common.noTeam")}</div>
                    </TableCell>
                    <TableCell>
                      {hasNeeds ? (
                        // Product types fully loaded, as in the Ploeg Wizard: green once complete.
                        <div className="flex min-w-40 items-center gap-3">
                          <div
                            className="h-2 flex-1 overflow-hidden rounded-full bg-muted"
                            role="progressbar"
                            aria-valuemin={0}
                            aria-valuemax={kar.required_product_count}
                            aria-valuenow={kar.loaded_product_count}
                          >
                            <div
                              className={complete ? "h-full bg-green-600" : "h-full bg-primary"}
                              style={{ width: `${percent}%` }}
                            />
                          </div>
                          <span className="text-sm text-muted-foreground tabular-nums">
                            {tOverview("productsCount", {
                              done: kar.loaded_product_count,
                              total: kar.required_product_count,
                            })}
                          </span>
                        </div>
                      ) : (
                        <span className="text-sm text-muted-foreground">{tOverview("noNeeds")}</span>
                      )}
                    </TableCell>
                    <TableCell className="text-sm tabular-nums">
                      {hasNeeds &&
                        tOverview("piecesCount", { done: kar.loaded_toward_required, total: kar.required_total })}
                    </TableCell>
                    <TableCell className="sticky right-0 z-10 bg-background group-hover:bg-muted/50">
                      <div className="flex items-center justify-end gap-2">
                        {/* A kar that's out shows where it is, and can still be opened: loading it
                            then is a follow-up delivery to the festival. */}
                        {kar.is_out && <KarStatusBadge isOut />}
                        <Button size="sm" onClick={() => openKar(kar)}>
                          <Play className="size-4" />
                          {tOverview("load")}
                        </Button>
                        {hasNeeds && seasonId !== null && (
                          <a
                            href={stockMasterLoadListPdfUrl(kar.kar_id, seasonId, locale)}
                            target="_blank"
                            rel="noreferrer"
                            title={tOverview("loadList")}
                            aria-label={tOverview("loadList")}
                            className={buttonVariants({ variant: "ghost", size: "icon-sm" })}
                          >
                            <FileText />
                          </a>
                        )}
                      </div>
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </div>
      )}
    </div>
  );
}
