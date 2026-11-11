"use client";

// The frame of every public kar page (what the karblad's QR code opens: the
// landing with its two tiles, the intervention form and Kar inventaris). No
// login, phone-first, in the RWCrew Pi app's look: the colour tokens are the
// `.kar-qr` variables in globals.css (copied from the Pi's Theme.qml), cards
// are rounded 14px and every tappable thing is at least 52px high.

import type { ReactNode } from "react";
import Image from "next/image";
import { useLocale, useTranslations } from "next-intl";
import { useSearchParams } from "next/navigation";
import { ChevronLeft } from "lucide-react";

import { Link, usePathname } from "@/i18n/navigation";
import { cn } from "@/lib/utils";

interface KarQrShellProps {
  /** The kar number shown as a chip in the header (when known). */
  karNumber?: string;
  /** Where the back arrow goes (the landing page); no arrow without it. */
  backHref?: string;
  /** Content width: "narrow" for forms, "wide" for the inventory list. */
  width?: "narrow" | "wide";
  children: ReactNode;
}

export function KarQrShell({ karNumber, backHref, width = "narrow", children }: KarQrShellProps) {
  const t = useTranslations("karQr");
  const locale = useLocale();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  // The same page in the other language, keeping the kar's query string.
  const otherLocale = locale === "nl" ? "en" : "nl";
  const query = searchParams.toString();

  return (
    <div className="kar-qr min-h-dvh bg-[var(--kq-bg)] text-[var(--kq-text)]">
      {/* Header bar: back arrow, logo, kar chip, language. */}
      <header className="sticky top-0 z-30 border-b border-[var(--kq-border)] bg-[var(--kq-surface)]/95 backdrop-blur">
        <div className={cn("mx-auto flex h-[58px] items-center gap-3 px-4", width === "wide" ? "max-w-3xl" : "max-w-xl")}>
          {backHref ? (
            <Link
              href={backHref}
              aria-label={t("back")}
              className="-ml-2 flex size-11 shrink-0 items-center justify-center rounded-[10px] text-[var(--kq-muted)] hover:bg-[var(--kq-raised)] hover:text-[var(--kq-text)]"
            >
              <ChevronLeft className="size-6" />
            </Link>
          ) : null}
          <Image src="/teamkar-logo.png" alt="TeamKar" width={68} height={40} className="h-9 w-auto shrink-0" priority />
          <div className="min-w-0 flex-1" />
          {karNumber ? (
            <span className="truncate rounded-full bg-[color-mix(in_srgb,var(--kq-teal)_var(--kq-soft-alpha),transparent)] px-3 py-1 text-sm font-bold tracking-wide text-[var(--kq-teal)]">
              {karNumber}
            </span>
          ) : null}
          <Link
            href={`${pathname}${query ? `?${query}` : ""}`}
            locale={otherLocale}
            className="flex h-9 shrink-0 items-center rounded-[10px] border border-[var(--kq-border)] px-3 text-xs font-semibold uppercase text-[var(--kq-muted)] hover:text-[var(--kq-text)]"
          >
            {otherLocale}
          </Link>
        </div>
      </header>
      <main className={cn("mx-auto px-4 pb-28 pt-5", width === "wide" ? "max-w-3xl" : "max-w-xl")}>{children}</main>
    </div>
  );
}

/** A Pi-style card: surface colour, border, rounded 14px. */
export function KarQrCard({ className, children }: { className?: string; children: ReactNode }) {
  return (
    <div className={cn("rounded-[14px] border border-[var(--kq-border)] bg-[var(--kq-surface)] p-4", className)}>
      {children}
    </div>
  );
}
