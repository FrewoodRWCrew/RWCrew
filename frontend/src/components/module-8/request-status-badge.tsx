// A special request's status as a small pill in the status's own colour
// (the palette of lib/status-colors.ts, as set on the Request statuses
// screen) — used by the wizard, the Ploegfiche and the follow-up table.

import { STATUS_COLOR_INFO, isStatusColorKey } from "@/lib/status-colors";
import { cn } from "@/lib/utils";

interface RequestStatusBadgeProps {
  name: string;
  color: string;
}

export function RequestStatusBadge({ name, color }: RequestStatusBadgeProps) {
  const info = isStatusColorKey(color) ? STATUS_COLOR_INFO[color] : null;
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full border px-2 py-0.5 text-xs font-medium whitespace-nowrap",
        info?.textClassName ?? "text-muted-foreground",
      )}
    >
      <span className={cn("inline-block size-2 rounded-full", info?.swatchClassName ?? "bg-muted-foreground")} />
      {name}
    </span>
  );
}
