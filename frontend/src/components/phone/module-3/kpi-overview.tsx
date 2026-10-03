// The phone's KPI overview: three numbers (total, open, closed) and two
// simple bar lists — requests per status (in the status colours) and per
// team. Plain bars instead of the desktop's charts, so they stay readable
// on a narrow screen.

import { getTranslations } from "next-intl/server";
import { isStatusColorKey, STATUS_COLOR_INFO } from "@/lib/status-colors";
import type { InterventionRequestsDashboardStats } from "@/lib/types";
import { PhoneBody } from "@/components/phone/shared/phone-body";

// A bar with a count above zero is always drawn at least this wide (in %).
const MIN_BAR_PERCENT = 3;

interface BarItem {
  label: string;
  count: number;
  /** Tailwind background class of the bar. */
  barClassName: string;
}

export async function KpiOverview({ stats }: { stats: InterventionRequestsDashboardStats }) {
  const t = await getTranslations("interventionRequests.landing");

  const statusBars: BarItem[] = stats.status_breakdown.map((item) => ({
    label: item.status_name,
    count: item.count,
    barClassName: STATUS_COLOR_INFO[isStatusColorKey(item.color) ? item.color : "gray"].swatchClassName,
  }));
  const teamBars: BarItem[] = stats.team_breakdown.map((item) => ({
    label: item.team_name,
    count: item.count,
    barClassName: "bg-orange-600",
  }));

  return (
    <PhoneBody>
      <div className="grid grid-cols-3 gap-2">
        <StatCard label={t("statTotalRequests")} value={stats.total_requests} />
        <StatCard label={t("statOpenRequests")} value={stats.open_requests} />
        <StatCard label={t("statClosedRequests")} value={stats.closed_requests} />
      </div>
      <BarCard title={t("chartStatusTitle")} description={t("chartStatusDescription")} items={statusBars} emptyText={t("chartEmpty")} />
      <BarCard title={t("chartTeamTitle")} description={t("chartTeamDescription")} items={teamBars} emptyText={t("chartEmpty")} />
    </PhoneBody>
  );
}

/** One big number with its label underneath. */
function StatCard({ label, value }: { label: string; value: number }) {
  return (
    <div className="flex flex-col items-center gap-1 rounded-xl border bg-card p-3 text-center">
      <span className="text-3xl font-bold text-orange-600 dark:text-orange-400">{value}</span>
      <span className="text-xs text-muted-foreground">{label}</span>
    </div>
  );
}

interface BarCardProps {
  title: string;
  description: string;
  items: BarItem[];
  emptyText: string;
}

/** A titled list of horizontal bars, each as long as its share of the largest count. */
function BarCard({ title, description, items, emptyText }: BarCardProps) {
  const largest = Math.max(0, ...items.map((item) => item.count));

  return (
    <section className="flex flex-col gap-3 rounded-xl border bg-card p-4">
      <div>
        <h2 className="font-semibold">{title}</h2>
        <p className="text-sm text-muted-foreground">{description}</p>
      </div>
      {largest === 0 ? (
        <p className="text-sm text-muted-foreground">{emptyText}</p>
      ) : (
        items.map((item) => {
          const percent = item.count > 0 ? Math.max(MIN_BAR_PERCENT, (item.count / largest) * 100) : 0;
          return (
            <div key={item.label} className="flex flex-col gap-1">
              <div className="flex justify-between gap-2 text-sm">
                <span className="truncate">{item.label}</span>
                <span className="font-medium tabular-nums">{item.count}</span>
              </div>
              <div className="h-2.5 rounded-full bg-muted">
                <div className={`h-full rounded-full ${item.barClassName}`} style={{ width: `${percent}%` }} />
              </div>
            </div>
          );
        })
      )}
    </section>
  );
}
