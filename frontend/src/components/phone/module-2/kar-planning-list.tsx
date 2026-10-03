"use client";

// The phone's Kar Planning: a season dropdown, a search box and one card per
// kar (number, status, ploeg, transport type). Tapping a card opens it to
// show the planned afleverlocatie per festival, its location and a "Toon op
// kaart" link. Only one card is open at a time.

import { useEffect, useMemo, useRef, useState } from "react";
import { ChevronDown } from "lucide-react";
import { useTranslations } from "next-intl";
import { Link } from "@/i18n/navigation";
import { listKarPlanning } from "@/lib/api";
import type { KarTrackerKarPlanningReport, KarTrackerKarPlanningRow, KarTrackerSeasonOption } from "@/lib/types";
import { cn } from "@/lib/utils";
import { Button, buttonVariants } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { karTrackerPhoneRoutes } from "@/components/phone/module-2/kartracker-phone-routes";
import { PhoneNotice } from "@/components/phone/shared/phone-notice";
import { PhoneSelect } from "@/components/phone/shared/phone-select";

// The season dropdown's "no season" entry (a <select> value is always a string).
const NO_SEASON_VALUE = "";

interface KarPlanningListProps {
  seasons: KarTrackerSeasonOption[];
  initialSeasonId: number | null;
  initialReport: KarTrackerKarPlanningReport;
  /** Whether to offer "Toon op kaart" (needs the Kar Map right). */
  canViewMap: boolean;
}

/** Every text of a kar the search box looks in. */
function searchableText(row: KarTrackerKarPlanningRow): string {
  return [
    row.kar_nummer,
    row.status_name,
    row.team_name ?? "",
    row.transport_type_name,
    row.geolocation ?? "",
    ...Object.values(row.afleverlocaties),
  ]
    .join(" ")
    .toLowerCase();
}

export function KarPlanningList({ seasons, initialSeasonId, initialReport, canViewMap }: KarPlanningListProps) {
  const t = useTranslations("karTracker.phone.planning");
  const tCommon = useTranslations("common");
  const [seasonId, setSeasonId] = useState<number | null>(initialSeasonId);
  const [report, setReport] = useState(initialReport);
  const [isLoading, setIsLoading] = useState(false);
  const [loadFailed, setLoadFailed] = useState(false);
  // Bumped by "Opnieuw proberen" to load the same season again.
  const [reloadToken, setReloadToken] = useState(0);
  const [search, setSearch] = useState("");
  const [openKarId, setOpenKarId] = useState<number | null>(null);

  // Load the report again whenever the season changes (or on a retry). The
  // `cancelled` flag drops an answer that arrives after another choice.
  const isFirstLoadRef = useRef(true);
  useEffect(() => {
    // The first season's report already came from the server.
    if (isFirstLoadRef.current) {
      isFirstLoadRef.current = false;
      return;
    }
    let cancelled = false;
    listKarPlanning(seasonId)
      .then((nextReport) => {
        if (cancelled) return;
        setReport(nextReport);
        setLoadFailed(false);
      })
      .catch(() => {
        if (!cancelled) setLoadFailed(true);
      })
      .finally(() => {
        if (!cancelled) setIsLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [seasonId, reloadToken]);

  function handleSeasonChange(value: string) {
    setIsLoading(true);
    setSeasonId(value === NO_SEASON_VALUE ? null : Number(value));
  }

  function handleRetry() {
    setIsLoading(true);
    setReloadToken((token) => token + 1);
  }

  // The karren matching the search box.
  const visibleRows = useMemo(() => {
    const needle = search.trim().toLowerCase();
    return needle ? report.rows.filter((row) => searchableText(row).includes(needle)) : report.rows;
  }, [report, search]);

  return (
    <div className="flex flex-col gap-3">
      <div className="flex flex-col gap-2">
        <Label htmlFor="phone-planning-season">{t("seasonLabel")}</Label>
        <PhoneSelect
          id="phone-planning-season"
          value={seasonId ?? NO_SEASON_VALUE}
          onChange={(event) => handleSeasonChange(event.target.value)}
        >
          <option value={NO_SEASON_VALUE}>{t("noSeason")}</option>
          {seasons.map((season) => (
            <option key={season.id} value={season.id}>
              {season.name}
            </option>
          ))}
        </PhoneSelect>
      </div>
      <Input
        value={search}
        onChange={(event) => setSearch(event.target.value)}
        placeholder={t("searchPlaceholder")}
        className="h-11 text-base"
      />

      {isLoading && <p className="text-sm text-muted-foreground">{tCommon("loading")}</p>}
      {loadFailed && (
        <div className="flex items-center justify-between gap-2 text-sm text-destructive">
          <span>{t("loadError")}</span>
          <Button variant="outline" size="sm" onClick={handleRetry}>
            {t("retry")}
          </Button>
        </div>
      )}

      {visibleRows.length === 0 ? (
        <PhoneNotice>{t("noKarren")}</PhoneNotice>
      ) : (
        visibleRows.map((row) => (
          <KarPlanningCard
            key={row.id}
            row={row}
            report={report}
            isOpen={openKarId === row.id}
            onToggle={() => setOpenKarId((current) => (current === row.id ? null : row.id))}
            canViewMap={canViewMap}
          />
        ))
      )}
    </div>
  );
}

interface KarPlanningCardProps {
  row: KarTrackerKarPlanningRow;
  report: KarTrackerKarPlanningReport;
  isOpen: boolean;
  onToggle: () => void;
  canViewMap: boolean;
}

/** One kar: the summary is always shown, the details only when opened. */
function KarPlanningCard({ row, report, isOpen, onToggle, canViewMap }: KarPlanningCardProps) {
  const t = useTranslations("karTracker.phone.planning");

  return (
    <div className="rounded-xl border bg-card">
      <button type="button" onClick={onToggle} className="flex w-full flex-col gap-1 p-3 text-left">
        <span className="flex items-center gap-2">
          <span className="text-lg font-bold">{row.kar_nummer}</span>
          <span className="rounded-full border border-primary px-2 text-xs">{row.status_name}</span>
          <ChevronDown className={cn("ml-auto size-5 text-muted-foreground transition-transform", isOpen && "rotate-180")} />
        </span>
        <span className="text-sm">{row.team_name ?? t("noTeam")}</span>
        <span className="text-xs text-muted-foreground">
          {t("transportType")}: {row.transport_type_name}
        </span>
      </button>

      {isOpen && (
        <div className="flex flex-col gap-2 border-t p-3 text-sm">
          {/* The planned afleverlocatie per festival of the chosen season. */}
          {report.festivals.length === 0 ? (
            <p className="text-muted-foreground">{t("noFestivals")}</p>
          ) : (
            report.festivals.map((festival) => (
              <p key={festival.id}>
                <span className="font-medium">{festival.name}:</span> {row.afleverlocaties[festival.id] ?? "—"}
              </p>
            ))
          )}
          <p>
            <span className="font-medium">{t("geolocation")}:</span> {row.geolocation ?? t("noGeolocation")}
          </p>
          {canViewMap && row.geolocation && (
            <Link href={karTrackerPhoneRoutes.map(`kar-${row.id}`)} className={cn(buttonVariants(), "h-11 text-base")}>
              {t("showOnMap")}
            </Link>
          )}
        </div>
      )}
    </div>
  );
}
