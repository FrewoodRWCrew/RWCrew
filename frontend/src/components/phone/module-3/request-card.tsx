// One intervention request in the "Akties" list: number and status pill,
// the ploeg, the question (two lines at most) and time + delivery location.
// Tapping it opens the request.

import { Link } from "@/i18n/navigation";
import { formatTime } from "@/lib/date-time";
import type { InterventionRequest, InterventionStatus } from "@/lib/types";
import { interventionRequestsPhoneRoutes } from "@/components/phone/module-3/intervention-requests-phone-routes";
import { RequestStatusPill } from "@/components/phone/module-3/request-status-pill";

interface RequestCardProps {
  request: InterventionRequest;
  status: InterventionStatus | undefined;
  teamLabel: string;
}

export function RequestCard({ request, status, teamLabel }: RequestCardProps) {
  // "HH:mm" of the preferred delivery, in Belgian time like on the desktop.
  const deliveryTime = formatTime(request.preferred_delivery_at);
  const whenWhere = [deliveryTime, request.delivery_location].filter(Boolean).join(" · ");

  return (
    <Link
      href={interventionRequestsPhoneRoutes.request(request.id)}
      className="flex flex-col gap-1 rounded-xl border bg-card p-3 active:bg-muted"
    >
      <span className="flex items-center justify-between gap-2">
        <span className="font-bold">{request.request_number}</span>
        <RequestStatusPill status={status} />
      </span>
      <span className="truncate font-semibold">{teamLabel}</span>
      <span className="line-clamp-2 text-sm text-muted-foreground">{request.question}</span>
      {whenWhere && <span className="text-xs">{whenWhere}</span>}
    </Link>
  );
}
