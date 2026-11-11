"use client";

// The public kar page the karblad's QR code opens (no login): the kar's
// number, team and zone, and two big tiles — "Interventie aanvragen" (the
// existing intervention-request form, Interventies' orange) and "Kar
// inventaris" (count what is in the kar before pick-up, StockMaster's teal).
// Both tiles pass the QR code's query string on so the forms stay prefilled.

import type { ComponentType } from "react";
import { useTranslations } from "next-intl";
import { ChevronRight, ClipboardList, LifeBuoy, MapPin, Users } from "lucide-react";

import { Link } from "@/i18n/navigation";
import { karQrQuery, type KarQrParams } from "@/lib/kar-qr-params";
import { KarQrCard, KarQrShell } from "./kar-qr-shell";

interface KarQrLandingProps {
  params: KarQrParams;
  /** The team's name looked up from team_id (or the QR's own team_name). */
  teamName: string | null;
}

export function KarQrLanding({ params, teamName }: KarQrLandingProps) {
  const t = useTranslations("karQr");
  const query = karQrQuery(params);

  return (
    <KarQrShell karNumber={params.cart_number}>
      {/* The kar itself: big number like on the karblad. */}
      <KarQrCard className="mb-5 p-5">
        <p className="text-xs font-semibold uppercase tracking-[0.14em] text-[var(--kq-muted)]">{t("karBox")}</p>
        <p className="mt-1 text-5xl font-black tracking-tight">{params.cart_number ?? t("unknownKar")}</p>
        {teamName || params.zone || params.delivery_location ? (
          <div className="mt-4 flex flex-col gap-2 text-sm text-[var(--kq-muted)]">
            {teamName ? (
              <span className="flex items-center gap-2">
                <Users className="size-4 shrink-0" />
                <span className="font-semibold text-[var(--kq-text)]">{teamName}</span>
              </span>
            ) : null}
            {params.delivery_location || params.zone ? (
              <span className="flex items-center gap-2">
                <MapPin className="size-4 shrink-0" />
                <span>{[params.zone, params.delivery_location].filter(Boolean).join(" · ")}</span>
              </span>
            ) : null}
          </div>
        ) : null}
      </KarQrCard>

      <p className="mb-3 text-lg font-semibold">{t("question")}</p>
      <div className="grid gap-3 sm:grid-cols-2">
        <Tile
          href={`/kar/intervention-request${query}`}
          icon={LifeBuoy}
          colour="var(--kq-orange)"
          title={t("interventionTitle")}
          description={t("interventionDescription")}
        />
        <Tile
          href={`/kar/inventory${query}`}
          icon={ClipboardList}
          colour="var(--kq-teal)"
          title={t("inventoryTitle")}
          description={t("inventoryDescription")}
        />
      </div>
    </KarQrShell>
  );
}

interface TileProps {
  href: string;
  icon: ComponentType<{ className?: string }>;
  colour: string;
  title: string;
  description: string;
}

/** One big tappable tile: coloured icon square, title, one line, arrow. */
function Tile({ href, icon: Icon, colour, title, description }: TileProps) {
  return (
    <Link
      href={href}
      style={{ ["--tile" as string]: colour }}
      className="group flex min-h-[132px] items-center gap-4 rounded-[14px] border border-[var(--kq-border)] bg-[var(--kq-surface)] p-5 transition hover:border-[var(--tile)] active:scale-[0.99] sm:flex-col sm:items-start"
    >
      <span className="flex size-14 shrink-0 items-center justify-center rounded-[12px] bg-[var(--tile)] text-white shadow-[0_8px_24px_-8px_var(--tile)]">
        <Icon className="size-7" />
      </span>
      <span className="flex min-w-0 flex-1 flex-col gap-1">
        <span className="text-lg font-bold leading-tight">{title}</span>
        <span className="text-sm text-[var(--kq-muted)]">{description}</span>
      </span>
      <ChevronRight className="size-6 shrink-0 text-[var(--kq-faint)] transition group-hover:translate-x-0.5 group-hover:text-[var(--tile)] sm:hidden" />
    </Link>
  );
}
