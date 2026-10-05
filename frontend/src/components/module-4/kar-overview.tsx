"use client";

// StockMaster's "Karren": every kar of KarTracker as a card — number, team,
// in the warehouse or "onderweg", what's in it, and how far it's loaded
// against this season's needs ("18 / 20", green when complete, orange when
// partial). Typing a kar number and pressing Enter jumps straight to it.
// Filters (search, team, in/out) are remembered in this browser.

import { useEffect, useMemo, useState } from "react";
import { useTranslations } from "next-intl";
import { toast } from "sonner";
import { Link, useRouter } from "@/i18n/navigation";
import { listStockMasterKars } from "@/lib/api";
import type { Season, StockMasterKarSummary } from "@/lib/types";
import { cn } from "@/lib/utils";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { KarStatusBadge } from "@/components/module-4/stock-pickers";
import { StockMasterSeasonSelect, useStockMasterSeasonId } from "@/components/module-4/stockmaster-season-select";
import { STOCKMASTER_BASE, readRemembered, remember } from "@/components/module-4/stockmaster-common";

interface KarOverviewProps {
  seasons: Season[];
}

type Place = "all" | "in" | "out";

export function KarOverview({ seasons }: KarOverviewProps) {
  const t = useTranslations("stockMaster");
  const router = useRouter();
  const seasonId = useStockMasterSeasonId(seasons);
  const [kars, setKars] = useState<StockMasterKarSummary[] | null>(null);
  const [search, setSearch] = useState("");
  const [teamName, setTeamName] = useState<string>(() => readRemembered("karTeam", "all"));
  const [place, setPlace] = useState<Place>(() => readRemembered<Place>("karPlace", "all"));

  useEffect(() => {
    listStockMasterKars(seasonId)
      .then(setKars)
      .catch(() => toast.error(t("errors.loadFailed")));
  }, [seasonId, t]);

  const teams = useMemo(
    () => [...new Set((kars ?? []).map((kar) => kar.team_name).filter((name): name is string => Boolean(name)))].sort(),
    [kars],
  );

  const visible = (kars ?? []).filter((kar) => {
    const needle = search.trim().toLowerCase();
    return (
      (!needle || kar.kar_nummer.toLowerCase().includes(needle) || (kar.team_name ?? "").toLowerCase().includes(needle)) &&
      (teamName === "all" || kar.team_name === teamName) &&
      (place === "all" || (place === "out" ? kar.is_out : !kar.is_out))
    );
  });

  function detailHref(kar: StockMasterKarSummary) {
    return `${STOCKMASTER_BASE}/kars/${kar.kar_id}${seasonId ? `?season=${seasonId}` : ""}`;
  }

  // Enter on an exact kar number (or the only match) opens that kar.
  function handleSearchKey(event: React.KeyboardEvent<HTMLInputElement>) {
    if (event.key !== "Enter") return;
    const exact = visible.find((kar) => kar.kar_nummer.toLowerCase() === search.trim().toLowerCase());
    const target = exact ?? (visible.length === 1 ? visible[0] : null);
    if (target) router.push(detailHref(target));
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight underline">{t("kars.title")}</h1>
          <p className="text-muted-foreground">{t("kars.description")}</p>
        </div>
        <StockMasterSeasonSelect seasons={seasons} seasonId={seasonId} />
      </div>

      <div className="flex flex-wrap items-end gap-3">
        <div className="flex w-64 flex-col gap-2">
          <Label htmlFor="kars-search">{t("common.search")}</Label>
          <Input
            id="kars-search"
            autoFocus
            placeholder={t("common.karSearchPlaceholder")}
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            onKeyDown={handleSearchKey}
          />
        </div>
        <div className="flex w-56 flex-col gap-2">
          <Label htmlFor="kars-team">{t("common.team")}</Label>
          <Select
            value={teamName}
            onValueChange={(value) => {
              setTeamName(value ?? "all");
              remember("karTeam", value ?? "all");
            }}
          >
            <SelectTrigger id="kars-team" className="w-full">
              <SelectValue>{(value: string | null) => (value === "all" || !value ? t("common.all") : value)}</SelectValue>
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">{t("common.all")}</SelectItem>
              {teams.map((name) => (
                <SelectItem key={name} value={name}>
                  {name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div className="flex gap-1">
          {(["all", "in", "out"] as Place[]).map((option) => (
            <button
              key={option}
              type="button"
              onClick={() => {
                setPlace(option);
                remember("karPlace", option);
              }}
              className={cn(
                "h-8 rounded-md border px-3 text-sm",
                place === option ? "bg-primary text-primary-foreground" : "bg-background hover:bg-muted",
              )}
            >
              {t(`kars.place.${option}`)}
            </button>
          ))}
        </div>
      </div>

      {kars === null && <p className="text-sm text-muted-foreground">{t("common.loading")}</p>}
      {kars !== null && visible.length === 0 && <p className="text-sm text-muted-foreground">{t("kars.empty")}</p>}

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
        {visible.map((kar) => {
          const hasNeeds = kar.required_total > 0;
          const complete = hasNeeds && kar.loaded_toward_required >= kar.required_total;
          const percent = hasNeeds ? Math.round((kar.loaded_toward_required / kar.required_total) * 100) : 0;
          return (
            <Link key={kar.kar_id} href={detailHref(kar)} className="rounded-xl focus-visible:ring-2 focus-visible:ring-ring">
              <Card className="h-full transition-colors hover:bg-muted/40">
                <CardContent className="flex flex-col gap-3">
                  <div className="flex items-start justify-between gap-2">
                    <div>
                      <div className="text-xl font-bold">{kar.kar_nummer}</div>
                      <div className="text-sm text-muted-foreground">{kar.team_name ?? t("common.noTeam")}</div>
                    </div>
                    <KarStatusBadge isOut={kar.is_out} />
                  </div>
                  <div className="text-sm">
                    {kar.is_out && kar.trip
                      ? t("kars.outWith", { festival: kar.trip.festival_name ?? kar.trip.team_name ?? "—" })
                      : t("kars.contents", { products: kar.product_count, pieces: kar.total_quantity })}
                  </div>
                  {hasNeeds ? (
                    <div className="flex flex-col gap-1">
                      <div className="flex justify-between text-xs">
                        <span className="text-muted-foreground">{t("kars.loaded")}</span>
                        <span className={cn("font-semibold tabular-nums", complete ? "text-green-700 dark:text-green-400" : "text-orange-700 dark:text-orange-300")}>
                          {kar.loaded_toward_required} / {kar.required_total}
                        </span>
                      </div>
                      <div className="h-2 overflow-hidden rounded-full bg-muted">
                        <div
                          className={cn("h-full rounded-full", complete ? "bg-green-600" : "bg-orange-500")}
                          style={{ width: `${percent}%` }}
                        />
                      </div>
                    </div>
                  ) : (
                    <div className="text-xs text-muted-foreground">{t("kars.noNeeds")}</div>
                  )}
                </CardContent>
              </Card>
            </Link>
          );
        })}
      </div>
    </div>
  );
}
