"use client";

// "Hoe is dit berekend?": the flow diagram behind one Kar laden row's
// "Op dit moment beschikbaar voor levering", with the row's own values filled
// in. The backend decides the outcome (module_4/delivery_entitlement.py) and
// sends the path of diagram nodes it took; this dialog only draws that path in
// the StockMaster accent colour and greys out the other branches. Below the
// diagram, the last step from kar-load-table.tsx's availableForDelivery: the
// outcome limited to what's physically there.

import { Diamond } from "lucide-react";
import { useTranslations } from "next-intl";
import type { ReactNode } from "react";
import type { StockMasterEntitlementTrace } from "@/lib/types";
import { cn } from "@/lib/utils";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import type { KarLoadRow } from "@/components/module-4/kar-load-table";

type LimitKind = StockMasterEntitlementTrace["limit_kind"];

// The four Limiet branches, left to right as on the organisation's diagram.
const LIMIT_KINDS: LimitKind[] = ["unlimited", "automatic", "percentage", "assigned"];

interface AvailabilityFlowDialogProps {
  /** The row whose calculation is shown; null keeps the dialog closed. */
  row: KarLoadRow | null;
  onClose: () => void;
}

export function AvailabilityFlowDialog({ row, onClose }: AvailabilityFlowDialogProps) {
  const t = useTranslations("stockMaster.karLoad");

  return (
    <Dialog open={row !== null} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-6xl">
        {row && (
          <>
            <DialogHeader>
              <DialogTitle>{t("flow.title", { name: row.name })}</DialogTitle>
              <DialogDescription>
                {t("flow.description", { source: row.source ? t(`sources.${row.source}`) : "—" })}
              </DialogDescription>
            </DialogHeader>
            {row.trace ? <FlowDiagram row={row} trace={row.trace} /> : <p className="text-muted-foreground">{t("flow.noTrace")}</p>}
          </>
        )}
      </DialogContent>
    </Dialog>
  );
}

/** The diagram itself: the three first questions, then the four Limiet branches, then the physical stock. */
function FlowDiagram({ row, trace }: { row: KarLoadRow; trace: StockMasterEntitlementTrace }) {
  const t = useTranslations("stockMaster.karLoad.flow");
  const on = (key: string) => trace.path.includes(key);
  const requested = trace.requested;

  return (
    <div className="space-y-1 text-sm">
      {/* Start: what the row asks. */}
      <FlowBox active kind="start" title={t("start")} value={String(requested)} />
      <Connector active />

      {/* Blokkeer → 0. */}
      <DecisionRow
        title={t("blocked")}
        answer={trace.is_blocked}
        active
        yes={<FlowBox active={on("result:zero")} kind="result" title={t("resultTitle")} value="0" />}
      />
      <Connector active={on("blocked:no")} label={t("no")} />

      {/* Is logistiek product → Gevraagd door vereniging. */}
      <DecisionRow
        title={t("logistics")}
        answer={trace.is_logistics_product}
        active={on("blocked:no")}
        yes={
          <FlowBox
            active={on("result:logistics")}
            kind="result"
            title={t("resultTitle")}
            formula={t("formulaRequested")}
            value={on("result:logistics") ? String(requested) : undefined}
          />
        }
      />
      <Connector active={on("logistics:no")} label={t("no")} />

      {/* Limiet: which branch the product's Limiet picks. */}
      <FlowBox
        active={on("logistics:no")}
        kind="decision"
        title={t("limit")}
        value={trace.limit_name ?? t("noLimit")}
      />
      <Connector active={on("logistics:no")} />

      <div className="grid gap-3 md:grid-cols-4">
        {LIMIT_KINDS.map((kind) => (
          <LimitBranch key={kind} kind={kind} trace={trace} on={on} />
        ))}
      </div>

      <Connector active />
      <PhysicalStep row={row} trace={trace} />
    </div>
  );
}

/** One Limiet branch (a column on wide screens). */
function LimitBranch({ kind, trace, on }: { kind: LimitKind; trace: StockMasterEntitlementTrace; on: (key: string) => boolean }) {
  const t = useTranslations("stockMaster.karLoad.flow");
  const taken = on(`limit:${kind}`);
  const requested = trace.requested;
  const percent = trace.share_percent;

  return (
    <div className="flex flex-col">
      <FlowBox active={taken} kind="branch" title={t(`kinds.${kind}`)} />
      <Connector active={taken} />

      {kind === "unlimited" && (
        <FlowBox
          active={on("result:unlimited")}
          kind="result"
          title={t("resultTitle")}
          formula={t("formulaRequested")}
          value={on("result:unlimited") ? String(requested) : undefined}
        />
      )}

      {kind === "automatic" && (
        <>
          {/* Enough stock for every kar? Yes → what was asked. */}
          <DecisionRow
            stacked
            title={t("shortage")}
            detail={taken ? t("shortageValues", { stock: trace.total_stock, demand: trace.season_demand }) : undefined}
            answer={on("shortage:no")}
            active={taken}
            yes={
              <FlowBox
                active={on("result:automatic_enough")}
                kind="result"
                title={t("resultTitle")}
                formula={t("formulaRequested")}
                value={on("result:automatic_enough") ? String(requested) : undefined}
              />
            }
          />
          <Connector active={on("calc:share")} />
          <FlowBox
            active={on("calc:share")}
            kind="step"
            title={t("calcShare")}
            formula={t("formulaShare")}
            value={
              on("calc:share") && percent !== null
                ? t("shareValues", { stock: trace.total_stock, demand: trace.season_demand, percent })
                : undefined
            }
          />
          <Connector active={on("calc:share")} />
          <FlowBox
            active={on("calc:share")}
            kind="step"
            title={t("rounded")}
            formula={t("formulaRounded")}
            value={
              on("calc:share") && percent !== null
                ? t("roundedValues", { requested, percent, result: trace.before_cap })
                : undefined
            }
          />
          <DeliveredStep kind={kind} trace={trace} on={on} active={on("calc:share")} />
        </>
      )}

      {kind === "percentage" && (
        <>
          <FlowBox
            active={taken}
            kind="step"
            title={t("rounded")}
            formula={t("formulaPercentage")}
            value={
              taken
                ? percent !== null
                  ? t("roundedValues", { requested, percent, result: trace.before_cap })
                  : t("percentageMissing", { result: trace.before_cap })
                : undefined
            }
          />
          <DeliveredStep kind={kind} trace={trace} on={on} active={taken} />
        </>
      )}

      {kind === "assigned" && (
        <>
          <FlowBox
            active={taken}
            kind="step"
            title={t("resultTitle")}
            formula={t("formulaRequested")}
            value={taken ? String(requested) : undefined}
          />
          <DeliveredStep kind={kind} trace={trace} on={on} active={taken} />
        </>
      )}
    </div>
  );
}

/** "Is de kar Geleverd?": yes keeps the value, no caps it at Maximum initiële stock. */
function DeliveredStep({
  kind,
  trace,
  on,
  active,
}: {
  kind: LimitKind;
  trace: StockMasterEntitlementTrace;
  on: (key: string) => boolean;
  active: boolean;
}) {
  const t = useTranslations("stockMaster.karLoad.flow");
  const yesTaken = on(`result:${kind}`);
  const noTaken = on(`result:${kind}_capped`);
  const max = trace.max_initial_stock;

  // The capped result's sentence: no maximum, the maximum, or what the Altsien row left of it.
  let cappedValue: string | undefined;
  if (noTaken) {
    if (max === null) cappedValue = t("noMax", { result: trace.entitled });
    else if (trace.cap_used_by_other_row > 0)
      cappedValue = t("cappedSharedValues", { before: trace.before_cap, max, used: trace.cap_used_by_other_row, result: trace.entitled });
    else cappedValue = t("cappedValues", { before: trace.before_cap, max, result: trace.entitled });
  }

  return (
    <>
      <Connector active={active} />
      <FlowBox
        active={active}
        kind="decision"
        title={t("delivered")}
        value={active ? t("deliveredValues", { status: trace.kar_status ?? t("noStatus") }) : undefined}
        answer={active ? trace.is_delivered : undefined}
      />
      <div className="grid grid-cols-2 gap-2">
        <div className="flex flex-col">
          <Connector active={yesTaken} label={t("yes")} />
          <FlowBox
            active={yesTaken}
            kind="result"
            title={t("resultTitle")}
            formula={t("formulaKeep")}
            value={yesTaken ? String(trace.entitled) : undefined}
          />
        </div>
        <div className="flex flex-col">
          <Connector active={noTaken} label={t("no")} />
          <FlowBox active={noTaken} kind="result" title={t("resultTitle")} formula={t("formulaCapped")} value={cappedValue} />
        </div>
      </div>
    </>
  );
}

/** The last step: the diagram's outcome limited to what's physically there (availableForDelivery). */
function PhysicalStep({ row, trace }: { row: KarLoadRow; trace: StockMasterEntitlementTrace }) {
  const t = useTranslations("stockMaster.karLoad.flow");
  const freeLeft = row.free - row.otherQuantity;
  const sentence =
    row.source === "manual"
      ? t("physicalManual", { entitled: trace.entitled, delivered: row.delivered, free: freeLeft, result: row.availableNow })
      : t("physicalAltsien", {
          entitled: trace.entitled,
          consumed: row.consumedOutside,
          inKar: row.inKar,
          free: freeLeft,
          result: row.availableNow,
        });

  return (
    <div className="rounded-lg border-2 border-teal-600 bg-teal-50 p-3 dark:bg-teal-500/10">
      <div className="font-semibold">{t("physicalTitle")}</div>
      <div className="mt-1 tabular-nums">{sentence}</div>
      <div className="mt-1 text-xs text-muted-foreground">{t("physicalHelp")}</div>
    </div>
  );
}

/** A question with its "Ja" outcome beside it (or below it when `stacked`); "Nee" continues downwards. */
function DecisionRow({
  title,
  detail,
  answer,
  active,
  yes,
  stacked = false,
}: {
  title: string;
  detail?: string;
  answer: boolean;
  active: boolean;
  yes: ReactNode;
  stacked?: boolean;
}) {
  const t = useTranslations("stockMaster.karLoad.flow");
  const yesTaken = active && answer;
  return (
    <div className={cn("flex gap-2", stacked ? "flex-col" : "flex-col sm:flex-row sm:items-center")}>
      <div className={cn(!stacked && "sm:w-1/2")}>
        <FlowBox active={active} kind="decision" title={title} value={detail} answer={active ? answer : undefined} />
      </div>
      {/* The "Ja" arm. */}
      <div className={cn("flex items-center gap-2", !stacked && "sm:w-1/2")}>
        <span className={cn("shrink-0 text-xs font-semibold", yesTaken ? "text-teal-700 dark:text-teal-300" : "text-muted-foreground/60")}>
          {t("yes")} →
        </span>
        <div className="flex-1">{yes}</div>
      </div>
      {stacked && (
        <span className={cn("text-xs font-semibold", active && !answer ? "text-teal-700 dark:text-teal-300" : "text-muted-foreground/60")}>
          {t("no")} ↓
        </span>
      )}
    </div>
  );
}

/** One box of the diagram, coloured when it's on the row's path. */
function FlowBox({
  active,
  kind,
  title,
  formula,
  value,
  answer,
}: {
  active: boolean;
  kind: "start" | "decision" | "branch" | "step" | "result";
  title: string;
  /** The rule in words (shown on every box, also greyed-out ones). */
  formula?: string;
  /** The row's own value (only on the path). */
  value?: string;
  /** A decision's answer for this row. */
  answer?: boolean;
}) {
  const t = useTranslations("stockMaster.karLoad.flow");
  return (
    <div
      className={cn(
        "border-2 px-3 py-2 text-center transition-opacity",
        kind === "decision" ? "rounded-md border-dashed" : kind === "branch" ? "rounded-full" : "rounded-lg",
        active
          ? "border-teal-600 bg-teal-50 dark:bg-teal-500/10"
          : "border-border bg-background text-muted-foreground opacity-50",
      )}
    >
      <div className="flex items-center justify-center gap-1.5 font-medium">
        {kind === "decision" && <Diamond className="size-3.5 shrink-0" />}
        <span>{title}</span>
      </div>
      {formula && <div className="text-xs text-muted-foreground">{formula}</div>}
      {value !== undefined && (
        <div className={cn("mt-0.5 tabular-nums", kind === "result" || kind === "start" ? "text-base font-bold" : "font-semibold")}>
          {value}
        </div>
      )}
      {answer !== undefined && (
        <div className="mt-0.5 text-xs font-semibold text-teal-700 dark:text-teal-300">{answer ? t("yes") : t("no")}</div>
      )}
    </div>
  );
}

/** A short vertical line between two boxes, coloured on the path, with an optional label. */
function Connector({ active, label }: { active: boolean; label?: string }) {
  return (
    <div className="flex flex-col items-center py-0.5">
      {label && (
        <span className={cn("text-xs font-semibold", active ? "text-teal-700 dark:text-teal-300" : "text-muted-foreground/60")}>
          {label}
        </span>
      )}
      <div className={cn("h-4 w-0.5", active ? "bg-teal-600" : "bg-border")} />
    </div>
  );
}
