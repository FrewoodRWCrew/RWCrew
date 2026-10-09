// The gentle "work is waiting" hint shown just above the landing page's
// "Overzicht Modules" title: one small pill per module, in that module's
// own soft colour (see lib/module-theme.ts), for every module that has
// something waiting for the current user (today only TagScan's waiting
// actions — see the landing page), with a softly pulsing dot to catch the
// eye without shouting. Each pill links straight to where the work is done.
// Rendered on the server; no client JavaScript needed.

import { Link } from "@/i18n/navigation";
import { getModuleTheme } from "@/lib/module-theme";
import { cn } from "@/lib/utils";

export interface PendingWorkItem {
  /** Stable React key, e.g. the module key. */
  key: string;
  /** The module the work belongs to, e.g. "module-1" — sets the pill's colour. */
  moduleKey: string;
  /** The full sentence, e.g. "TagScan: 7 lines are waiting to be processed". */
  text: string;
  href: string;
}

interface PendingWorkNoticeProps {
  items: PendingWorkItem[];
  /** The link label, e.g. "Review". */
  openLabel: string;
}

export function PendingWorkNotice({ items, openLabel }: PendingWorkNoticeProps) {
  if (items.length === 0) return null;

  return (
    <div className="flex flex-wrap gap-2">
      {items.map((item) => {
        // The module's soft tint (background + text) and its solid accent
        // colour (border + dot), the same colours as its landing tile.
        const { badgeClassName, accentColorToken } = getModuleTheme(item.moduleKey);
        const accentColor = `var(--color-${accentColorToken})`;
        return (
          <Link
            key={item.key}
            href={item.href}
            className={cn(
              "inline-flex w-fit items-center gap-2 rounded-full border px-3 py-1 text-sm transition-[filter] hover:brightness-95",
              badgeClassName,
            )}
            style={{ borderColor: `color-mix(in oklab, ${accentColor} 35%, transparent)` }}
          >
            {/* Pulsing dot: a fading halo over a solid dot. */}
            <span className="relative flex size-2.5">
              <span
                className="absolute inline-flex size-full animate-ping rounded-full opacity-60"
                style={{ backgroundColor: accentColor }}
              />
              <span className="relative inline-flex size-2.5 rounded-full" style={{ backgroundColor: accentColor }} />
            </span>
            <span>{item.text}</span>
            <span className="font-medium underline underline-offset-2">{openLabel} →</span>
          </Link>
        );
      })}
    </div>
  );
}
