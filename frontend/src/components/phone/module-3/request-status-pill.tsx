// A request's status as a small pill: a coloured dot and the name, in the
// status's own colour (the same palette as the desktop list, status-colors.ts).

import { isStatusColorKey, STATUS_COLOR_INFO } from "@/lib/status-colors";
import type { InterventionStatus } from "@/lib/types";
import { cn } from "@/lib/utils";

export function RequestStatusPill({ status }: { status: InterventionStatus | undefined }) {
  if (!status) return null;
  const colorInfo = STATUS_COLOR_INFO[isStatusColorKey(status.color) ? status.color : "gray"];

  return (
    <span
      className={cn(
        "inline-flex shrink-0 items-center gap-1.5 rounded-full border px-2 py-0.5 text-xs font-medium",
        colorInfo.textClassName,
      )}
    >
      <span className={cn("size-2 rounded-full", colorInfo.swatchClassName)} />
      {status.name}
    </span>
  );
}
