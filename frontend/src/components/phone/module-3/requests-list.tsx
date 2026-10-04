"use client";

// The "Akties" list: a search box, status chips ("Open" by default, "Alle",
// then one per status), and the matching requests as cards grouped per
// preferred delivery day, earliest first — requests without a preferred
// delivery come last. A round "+" button adds a request (with that right).

import { useMemo, useState } from "react";
import { Plus } from "lucide-react";
import { useTranslations } from "next-intl";
import { Link } from "@/i18n/navigation";
import type { InterventionRequest, InterventionRequestsTeam, InterventionStatus } from "@/lib/types";
import { cn } from "@/lib/utils";
import { Input } from "@/components/ui/input";
import { belgianDayKey, formatDateOnly, toDateTimeLocalValue, weekdayKeyFor } from "@/components/module-3/request-dates";
import { interventionRequestsPhoneRoutes } from "@/components/phone/module-3/intervention-requests-phone-routes";
import { RequestCard } from "@/components/phone/module-3/request-card";
import { PhoneNotice } from "@/components/phone/shared/phone-notice";

// The two fixed chips before the per-status ones.
const OPEN_FILTER = "open";
const ALL_FILTER = "all";

// The group of requests without a preferred delivery day.
const NO_DATE_KEY = "no-date";

interface RequestsListProps {
  requests: InterventionRequest[];
  statuses: InterventionStatus[];
  teams: InterventionRequestsTeam[];
  canCreate: boolean;
}

interface DayGroup {
  key: string;
  label: string;
  requests: InterventionRequest[];
}

/** Sort order: by preferred delivery (minute precision, Belgian time), undated last, then by number. */
function compareRequests(a: InterventionRequest, b: InterventionRequest): number {
  const aDate = toDateTimeLocalValue(a.preferred_delivery_at);
  const bDate = toDateTimeLocalValue(b.preferred_delivery_at);
  if (aDate !== bDate) {
    if (!aDate) return 1;
    if (!bDate) return -1;
    return aDate.localeCompare(bDate);
  }
  return a.request_number.localeCompare(b.request_number);
}

/** A request's ploeg: the MasterData team, or the name typed on the public form. */
function teamLabelFor(request: InterventionRequest, teamNameById: Map<number, string>): string {
  return (request.team_id !== null ? teamNameById.get(request.team_id) : undefined) ?? request.team_name ?? "";
}

export function RequestsList({ requests, statuses, teams, canCreate }: RequestsListProps) {
  const t = useTranslations("interventionRequests.phone");
  const tRequests = useTranslations("interventionRequests.requests");
  const [search, setSearch] = useState("");
  // OPEN_FILTER, ALL_FILTER, or a status id as text.
  const [filter, setFilter] = useState(OPEN_FILTER);

  const statusById = useMemo(() => new Map(statuses.map((status) => [status.id, status])), [statuses]);
  const teamNameById = useMemo(() => new Map(teams.map((team) => [team.id, team.name])), [teams]);

  // Filter, search, sort and group per day.
  const groups = useMemo<DayGroup[]>(() => {
    const needle = search.trim().toLowerCase();
    const visible = requests
      .filter((request) => {
        const status = statusById.get(request.status_id);
        // A status that can't be found counts as open.
        if (filter === OPEN_FILTER) return status?.is_open ?? true;
        if (filter === ALL_FILTER) return true;
        return String(request.status_id) === filter;
      })
      .filter((request) => {
        if (!needle) return true;
        return [
          request.request_number,
          teamLabelFor(request, teamNameById),
          request.question,
          request.employee_name,
          request.delivery_location,
          request.zone,
          request.cart_number,
        ].some((value) => value?.toLowerCase().includes(needle));
      })
      .sort(compareRequests);

    // Consecutive requests on the same day form one group (they are sorted).
    const result: DayGroup[] = [];
    for (const request of visible) {
      const day = belgianDayKey(request.preferred_delivery_at);
      const key = day || NO_DATE_KEY;
      let group = result.at(-1);
      if (!group || group.key !== key) {
        const label = day
          ? `${tRequests(`weekdays.${weekdayKeyFor(day)}`)} ${formatDateOnly(day)}`
          : t("noDeliveryDate");
        group = { key, label, requests: [] };
        result.push(group);
      }
      group.requests.push(request);
    }
    return result;
  }, [requests, statusById, teamNameById, filter, search, t, tRequests]);

  const chips = [
    { value: OPEN_FILTER, label: t("filterOpen") },
    { value: ALL_FILTER, label: t("filterAll") },
    ...statuses.map((status) => ({ value: String(status.id), label: status.name })),
  ];

  return (
    <div className="relative flex flex-1 flex-col gap-3 p-4 pb-24">
      <Input
        value={search}
        onChange={(event) => setSearch(event.target.value)}
        placeholder={t("searchPlaceholder")}
        className="h-11 text-base"
      />

      {/* Status chips, scrolling sideways when they don't fit. */}
      <div className="-mx-4 flex gap-2 overflow-x-auto px-4 pb-1">
        {chips.map((chip) => (
          <button
            key={chip.value}
            type="button"
            onClick={() => setFilter(chip.value)}
            className={cn(
              "shrink-0 rounded-full border px-3 py-1.5 text-sm",
              filter === chip.value ? "border-primary bg-primary font-medium text-primary-foreground" : "bg-background",
            )}
          >
            {chip.label}
          </button>
        ))}
      </div>

      {groups.length === 0 ? (
        <PhoneNotice>{t("noResults")}</PhoneNotice>
      ) : (
        groups.map((group) => (
          <section key={group.key} className="flex flex-col gap-2">
            {/* The day stays visible at the top while scrolling through it. */}
            <h2 className="sticky top-14 z-10 bg-background py-1 font-bold text-orange-600 dark:text-orange-400">
              {group.label}
            </h2>
            {group.requests.map((request) => (
              <RequestCard
                key={request.id}
                request={request}
                status={statusById.get(request.status_id)}
                teamLabel={teamLabelFor(request, teamNameById)}
              />
            ))}
          </section>
        ))
      )}

      {/* Floating "+" for a new request, above the tab bar. */}
      {canCreate && (
        <Link
          href={interventionRequestsPhoneRoutes.newRequest}
          aria-label={tRequests("newRequest")}
          className="fixed right-4 bottom-[calc(4.5rem+env(safe-area-inset-bottom))] z-30 flex size-14 items-center justify-center rounded-full bg-primary text-primary-foreground shadow-lg active:brightness-90"
        >
          <Plus className="size-7" />
        </Link>
      )}
    </div>
  );
}
