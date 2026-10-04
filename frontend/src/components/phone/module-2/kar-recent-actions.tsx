// "Laatste bewegingen": the kar's most recent movements as small cards
// (status and time, then ploeg and who logged it). Read-only.

import { getTranslations } from "next-intl/server";
import type { KarTrackerKarAction } from "@/lib/types";

// The backend's UTC timestamp in Belgian local time. A fixed time zone (not
// the runtime's default) keeps every phone and the server render identical.
const DATE_TIME_FORMAT = new Intl.DateTimeFormat("nl-BE", {
  timeZone: "Europe/Brussels",
  year: "numeric",
  month: "2-digit",
  day: "2-digit",
  hour: "2-digit",
  minute: "2-digit",
});

export async function KarRecentActions({ actions }: { actions: KarTrackerKarAction[] }) {
  const t = await getTranslations("karTracker.phone.kar");

  return (
    <section className="flex flex-col gap-2">
      <h2 className="font-bold underline">{t("historyTitle")}</h2>
      {actions.length === 0 ? (
        <p className="text-sm text-muted-foreground">{t("noHistory")}</p>
      ) : (
        actions.map((action) => (
          <div key={action.id} className="rounded-xl border bg-card p-3 text-sm">
            <div className="flex justify-between gap-2">
              <span className="font-medium">{action.status_name}</span>
              <span className="text-muted-foreground tabular-nums">
                {DATE_TIME_FORMAT.format(new Date(action.recorded_at))}
              </span>
            </div>
            <p className="text-muted-foreground">
              {action.team_name ?? t("noTeam")}
              {action.user_name && ` · ${t("by", { name: action.user_name })}`}
            </p>
          </div>
        ))
      )}
    </section>
  );
}
