// The gentle "work is waiting" hint shown just above the landing page's
// "Overzicht Modules" title: one small orange pill per module that has
// something waiting for the current user (today only TagScan's waiting
// actions — see the landing page), with a softly pulsing dot to catch the
// eye without shouting. Each pill links straight to where the work is done.
// Rendered on the server; no client JavaScript needed.

import { Link } from "@/i18n/navigation";

export interface PendingWorkItem {
  /** Stable React key, e.g. the module key. */
  key: string;
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
      {items.map((item) => (
        <Link
          key={item.key}
          href={item.href}
          className="inline-flex w-fit items-center gap-2 rounded-full border border-orange-500/30 bg-orange-500/10 px-3 py-1 text-sm text-orange-700 transition-colors hover:bg-orange-500/15 dark:text-orange-300"
        >
          {/* Pulsing dot: a fading halo over a solid dot. */}
          <span className="relative flex size-2.5">
            <span className="absolute inline-flex size-full animate-ping rounded-full bg-orange-500 opacity-60" />
            <span className="relative inline-flex size-2.5 rounded-full bg-orange-500" />
          </span>
          <span>{item.text}</span>
          <span className="font-medium underline underline-offset-2">{openLabel} →</span>
        </Link>
      ))}
    </div>
  );
}
