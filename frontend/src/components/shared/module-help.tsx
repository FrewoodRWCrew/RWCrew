"use client";

// The two ways into a module's help manual (a PDF made by the backend, see
// backend/app/help/):
// - ModuleHelpMenuLink: a "Help" group with "Handleiding (PDF)" at the
//   bottom of a module's own sidebar, the whole manual (only the screens the
//   user can view);
// - ScreenHelpButton: "Help bij dit scherm" above the page, only the chapter
//   about the screen that's open. The module passes its own route -> topic
//   list (e.g. components/module-4/stockmaster-help.ts); on a route without
//   a topic the button stays hidden;
// - HelpTopicLink: the same link for one fixed topic, for help about
//   something that isn't a route (e.g. TagScan's waiting-actions dialog).

import { BookOpen, CircleHelp } from "lucide-react";
import { useLocale, useTranslations } from "next-intl";
import { usePathname } from "@/i18n/navigation";
import { moduleHelpPdfUrl } from "@/lib/api";
import { cn } from "@/lib/utils";

/** One route of a module and the manual topic that explains it. `exact`
 *  routes only match themselves (the module's start page); the others also
 *  match their sub-pages (e.g. /kars/12). */
export interface HelpTopicRoute {
  path: string;
  topic: string;
  exact?: boolean;
}

/** The topic of the most specific route matching `pathname`, if any. */
export function findHelpTopic(pathname: string, routes: HelpTopicRoute[]): string | null {
  let best: HelpTopicRoute | null = null;
  for (const route of routes) {
    const matches = route.exact
      ? pathname === route.path
      : pathname === route.path || pathname.startsWith(`${route.path}/`);
    if (matches && (!best || route.path.length > best.path.length)) best = route;
  }
  return best?.topic ?? null;
}

interface ModuleHelpMenuLinkProps {
  moduleKey: string;
}

export function ModuleHelpMenuLink({ moduleKey }: ModuleHelpMenuLinkProps) {
  const t = useTranslations("help");
  const locale = useLocale();

  return (
    // A menu group of its own ("Help" heading + an underlined sub-item),
    // styled like the other groups of the module sidebars (e.g. MasterData's).
    <>
      <div className="flex items-center gap-3 px-3 pt-3 pb-1 text-xs font-semibold tracking-wide text-sidebar-foreground/50 uppercase">
        <BookOpen className="size-4" />
        {t("group")}
      </div>
      {/* Opens the PDF in a new tab (print or save from there), like the other PDFs. */}
      <a
        href={moduleHelpPdfUrl(moduleKey, locale)}
        target="_blank"
        rel="noopener noreferrer"
        className="ml-3 rounded-md px-3 py-2 text-sm font-medium text-sidebar-foreground/80 underline transition-colors hover:bg-sidebar-accent hover:text-sidebar-accent-foreground"
      >
        {t("manual")}
      </a>
    </>
  );
}

interface HelpTopicLinkProps {
  moduleKey: string;
  topic: string;
}

export function HelpTopicLink({ moduleKey, topic }: HelpTopicLinkProps) {
  const t = useTranslations("help");
  const locale = useLocale();

  return (
    <a
      href={moduleHelpPdfUrl(moduleKey, locale, topic)}
      target="_blank"
      rel="noopener noreferrer"
      className="inline-flex items-center gap-1.5 rounded-md px-2 py-1 text-xs font-medium text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
    >
      <CircleHelp className="size-4" />
      {t("screenHelp")}
    </a>
  );
}

interface ScreenHelpButtonProps {
  moduleKey: string;
  routes: HelpTopicRoute[];
  className?: string;
}

export function ScreenHelpButton({ moduleKey, routes, className }: ScreenHelpButtonProps) {
  // The path without the locale, e.g. "/modules/module-4/stock".
  const pathname = usePathname();
  const topic = findHelpTopic(pathname, routes);

  if (!topic) return null;

  return (
    <div className={cn("flex justify-end", className)}>
      <HelpTopicLink moduleKey={moduleKey} topic={topic} />
    </div>
  );
}
