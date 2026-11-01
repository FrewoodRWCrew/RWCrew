"use client";

// The Scans module's wristband "Scans" screen: every message that was received
// (the JSON files converted to a table), refused and ignored ones too, with
// filters on day, status, scanner and team. The filters are applied by the
// backend, which caps the table at its newest rows.

import { useState } from "react";
import { RefreshCw } from "lucide-react";
import { useTranslations } from "next-intl";
import { listWristbandScanners, listWristbandScans } from "@/lib/api";
import type { WristbandScan, WristbandScanFilters, WristbandScanner } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { SearchableSelect } from "@/components/ui/searchable-select";
import { ScanLogTable } from "@/components/shared/wristband/scan-log-table";
import { useKeyedLoad } from "@/components/module-4/use-keyed-load";

const STATUSES: WristbandScan["status"][] = ["new", "used", "dismissed", "ignored", "refused"];

export function WristbandScans({ canViewScanners }: { canViewScanners: boolean }) {
  const t = useTranslations("wristband.scans");
  const tLog = useTranslations("wristband.log");
  const [filters, setFilters] = useState<WristbandScanFilters>({ day: "", status: "", deviceId: "", team: "" });

  const scans = useKeyedLoad<WristbandScan[]>(JSON.stringify(filters), () => listWristbandScans(filters));
  const scanners = useKeyedLoad<WristbandScanner[]>(canViewScanners ? "wristband-scanners" : null, listWristbandScanners);

  function update(field: keyof WristbandScanFilters, value: string | null) {
    setFilters((current) => ({ ...current, [field]: value ?? "" }));
  }

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight underline">{t("title")}</h1>
          <p className="text-muted-foreground">{t("description")}</p>
        </div>
        <Button variant="outline" size="sm" onClick={scans.reload}>
          <RefreshCw className="size-4" />
          {tLog("refresh")}
        </Button>
      </div>

      <div className="flex flex-wrap items-end gap-4">
        <div className="flex flex-col gap-2">
          <Label htmlFor="wristband-filter-day">{t("day")}</Label>
          <Input id="wristband-filter-day" type="date" className="w-44" value={filters.day} onChange={(event) => update("day", event.target.value)} />
        </div>
        <div className="flex w-52 flex-col gap-2">
          <Label htmlFor="wristband-filter-status">{tLog("status")}</Label>
          <SearchableSelect
            id="wristband-filter-status"
            value={filters.status}
            onValueChange={(value) => update("status", value)}
            options={[{ value: "", label: t("all") }, ...STATUSES.map((status) => ({ value: status, label: tLog(`statuses.${status}`) }))]}
          />
        </div>
        {canViewScanners && (
          <div className="flex w-52 flex-col gap-2">
            <Label htmlFor="wristband-filter-scanner">{tLog("scanner")}</Label>
            <SearchableSelect
              id="wristband-filter-scanner"
              value={filters.deviceId}
              onValueChange={(value) => update("deviceId", value)}
              options={[
                { value: "", label: t("all") },
                ...(scanners.data ?? []).map((scanner) => ({
                  value: scanner.device_id,
                  label: scanner.label ?? scanner.device_name ?? scanner.device_id,
                })),
              ]}
            />
          </div>
        )}
        <div className="flex flex-col gap-2">
          <Label htmlFor="wristband-filter-team">{tLog("team")}</Label>
          <Input id="wristband-filter-team" className="w-52" value={filters.team} onChange={(event) => update("team", event.target.value)} />
        </div>
      </div>

      <ScanLogTable scans={scans.data ?? []} isLoading={scans.isLoading} />
    </div>
  );
}
