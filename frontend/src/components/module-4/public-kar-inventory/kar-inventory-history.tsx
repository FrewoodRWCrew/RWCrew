"use client";

// Kar inventaris: the kar's earlier inventories (newest first, the last 20),
// so the team sees what it counted before. Each is a card that opens to show
// its lines; lines that differ from what left with the kar are coloured.

import { useState } from "react";
import { useTranslations } from "next-intl";
import { ChevronDown, History, MessageSquare, User } from "lucide-react";

import { formatDateTimeNl } from "@/lib/date-time";
import type { KarInventory } from "@/lib/types";
import { cn } from "@/lib/utils";
import { DiffBadge } from "./kar-inventory-screen";

export function KarInventoryHistory({ history }: { history: KarInventory[] }) {
  const t = useTranslations("stockMaster.publicInventory");
  const [openId, setOpenId] = useState<number | null>(null);

  return (
    <section className="flex flex-col gap-3">
      <h2 className="flex items-center gap-2 text-lg font-bold">
        <History className="size-5 text-[var(--kq-muted)]" />
        {t("historyTitle")}
      </h2>
      {history.length === 0 ? (
        <p className="rounded-[14px] border border-dashed border-[var(--kq-border)] px-4 py-6 text-center text-sm text-[var(--kq-muted)]">
          {t("historyEmpty")}
        </p>
      ) : (
        history.map((inventory) => {
          const isOpen = openId === inventory.id;
          const complete = inventory.total_counted >= inventory.total_expected;
          return (
            <div key={inventory.id} className="overflow-hidden rounded-[14px] border border-[var(--kq-border)] bg-[var(--kq-surface)]">
              <button
                type="button"
                onClick={() => setOpenId(isOpen ? null : inventory.id)}
                aria-expanded={isOpen}
                className="flex w-full items-center gap-3 p-4 text-left"
              >
                <div className="min-w-0 flex-1">
                  <p className="font-semibold">{formatDateTimeNl(inventory.created_at)}</p>
                  <p className="flex items-center gap-1.5 truncate text-sm text-[var(--kq-muted)]">
                    <User className="size-3.5 shrink-0" />
                    {inventory.counted_by_name}
                  </p>
                </div>
                <span
                  className={cn(
                    "shrink-0 rounded-full px-2.5 py-1 text-sm font-bold",
                    complete
                      ? "bg-[color-mix(in_srgb,var(--kq-ok)_var(--kq-soft-alpha),transparent)] text-[var(--kq-ok)]"
                      : "bg-[color-mix(in_srgb,var(--kq-warn)_var(--kq-soft-alpha),transparent)] text-[var(--kq-warn)]",
                  )}
                >
                  {inventory.total_counted} / {inventory.total_expected}
                </span>
                <ChevronDown className={cn("size-5 shrink-0 text-[var(--kq-faint)] transition", isOpen && "rotate-180")} />
              </button>
              {isOpen ? (
                <div className="border-t border-[var(--kq-border)] bg-[var(--kq-raised)] px-4 py-3">
                  <ul className="flex flex-col divide-y divide-[var(--kq-border)]">
                    {inventory.lines.map((line) => (
                      <li key={line.id} className="flex items-center gap-2 py-2 text-sm">
                        <span className="min-w-0 flex-1 truncate">{line.product_name}</span>
                        {line.is_extra ? (
                          <span className="text-xs font-semibold text-[var(--kq-info)]">{t("extraBadge")}</span>
                        ) : (
                          <DiffBadge expected={line.expected} counted={line.counted} />
                        )}
                        <span className="w-16 shrink-0 text-right font-semibold tabular-nums">
                          {line.counted}
                          {line.is_extra ? null : <span className="text-[var(--kq-faint)]"> / {line.expected}</span>}
                        </span>
                      </li>
                    ))}
                  </ul>
                  {inventory.remark ? (
                    <p className="mt-2 flex gap-2 text-sm text-[var(--kq-muted)]">
                      <MessageSquare className="mt-0.5 size-4 shrink-0" />
                      <span className="whitespace-pre-line">{inventory.remark}</span>
                    </p>
                  ) : null}
                </div>
              ) : null}
            </div>
          );
        })
      )}
    </section>
  );
}
