"use client";

// Kar inventaris, step 2: the team counts what is in its kar. One card per
// product that left with the kar ("Vertrokken met de kar: 8") with a big −/+
// stepper; a badge compares the count with that number (green = all there,
// orange = fewer, blue = more). Products not on the list can be added
// ("Extra product"). Name is required, a remark optional. Opslaan stores a
// new inventory (it never changes stock); every list line needs a count, so
// empty ones are offered "set to 0" first. Pi app look (see kar-qr-shell.tsx).

import { useMemo, useState } from "react";
import { useTranslations } from "next-intl";
import { CheckCircle2, Loader2, Minus, Package, PackagePlus, Plus, Save, Truck, Warehouse, X } from "lucide-react";

import { ApiError, karInventoryProductImageUrl, listKarInventoryProducts, saveKarInventory } from "@/lib/api";
import { formatDateTimeNl } from "@/lib/date-time";
import type { KarInventory, KarInventoryContext, KarInventoryProductOption } from "@/lib/types";
import { cn } from "@/lib/utils";
import { KarQrCard } from "@/components/shared/kar-qr/kar-qr-shell";
import { Typeahead } from "@/components/module-4/typeahead";
import { KarInventoryHistory } from "./kar-inventory-history";

interface KarInventoryScreenProps {
  context: KarInventoryContext;
  token: string;
  /** After a save: reload the context (the history gets the new inventory). */
  onSaved: () => void;
  /** The token is no longer valid: back to the code. */
  onExpired: () => void;
}

/** An extra product the team added, with its count (null = not yet typed). */
interface ExtraLine {
  product: KarInventoryProductOption;
  counted: number | null;
}

export function KarInventoryScreen({ context, token, onSaved, onExpired }: KarInventoryScreenProps) {
  const t = useTranslations("stockMaster.publicInventory");
  // Counts per product of the list (missing = not counted yet; 0 is a count).
  const [counts, setCounts] = useState<Record<number, number>>({});
  const [extras, setExtras] = useState<ExtraLine[]>([]);
  const [name, setName] = useState("");
  const [remark, setRemark] = useState("");
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [askZero, setAskZero] = useState(false);
  const [saved, setSaved] = useState<KarInventory | null>(null);
  // The product list for "Extra product", loaded the first time it is opened.
  const [productOptions, setProductOptions] = useState<KarInventoryProductOption[] | null>(null);
  const [isAddingExtra, setIsAddingExtra] = useState(false);

  const countedLines = context.lines.filter((line) => counts[line.product_id] !== undefined).length;
  const uncounted = context.lines.length - countedLines + extras.filter((extra) => extra.counted === null).length;
  const totalExpected = context.lines.reduce((sum, line) => sum + line.expected, 0);
  const totalCounted =
    context.lines.reduce((sum, line) => sum + (counts[line.product_id] ?? 0), 0) +
    extras.reduce((sum, extra) => sum + (extra.counted ?? 0), 0);

  // Products that are already a line can't be added as an extra.
  const takenIds = useMemo(
    () => new Set([...context.lines.map((line) => line.product_id), ...extras.map((extra) => extra.product.id)]),
    [context.lines, extras],
  );

  function setCount(productId: number, value: number | null) {
    setCounts((current) => {
      const next = { ...current };
      if (value === null) delete next[productId];
      else next[productId] = value;
      return next;
    });
  }

  async function openExtra() {
    setIsAddingExtra(true);
    if (productOptions !== null) return;
    try {
      setProductOptions(await listKarInventoryProducts(token));
    } catch (caught) {
      if (caught instanceof ApiError && caught.status === 401) onExpired();
      else setProductOptions([]);
    }
  }

  async function save(fillZero: boolean) {
    setAskZero(false);
    setError(null);
    if (!name.trim()) {
      setError(t("errors.name_required"));
      return;
    }
    // Empty lines: ask first whether they are 0.
    if (uncounted > 0 && !fillZero) {
      setAskZero(true);
      return;
    }
    setIsSaving(true);
    try {
      const result = await saveKarInventory(token, {
        counted_by_name: name.trim(),
        remark: remark.trim() || null,
        lines: context.lines.map((line) => ({ product_id: line.product_id, counted: counts[line.product_id] ?? 0 })),
        extra: extras.map((extra) => ({ product_id: extra.product.id, counted: extra.counted ?? 0 })),
      });
      setSaved(result);
      setCounts({});
      setExtras([]);
      setRemark("");
      window.scrollTo({ top: 0, behavior: "smooth" });
      onSaved();
    } catch (caught) {
      if (caught instanceof ApiError && caught.status === 401) {
        onExpired();
        return;
      }
      const [key, param] = caught instanceof ApiError ? caught.message.split("|") : ["network"];
      const known = ["name_required", "line_missing", "list_changed", "duplicate_product", "unknown_product"];
      setError(known.includes(key) ? t(`errors.${key}`, { name: param ?? "" }) : t("errors.network"));
      if (key === "list_changed") onSaved();
    } finally {
      setIsSaving(false);
    }
  }

  return (
    <div className="flex flex-col gap-5">
      {/* The kar: number, team, out since / in the warehouse. */}
      <KarQrCard className="p-5">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <p className="text-xs font-semibold uppercase tracking-[0.14em] text-[var(--kq-muted)]">{t("title")}</p>
            <p className="mt-1 text-4xl font-black tracking-tight">{context.kar_nummer}</p>
            <p className="mt-1 line-clamp-2 text-[var(--kq-muted)]">
              {[context.team_name, context.season_name].filter(Boolean).join(" · ")}
            </p>
          </div>
          <StatusPill isOut={context.kar_is_out} since={context.dispatched_at} />
        </div>
        <p className="mt-4 text-sm text-[var(--kq-muted)]">{t("explanation")}</p>
      </KarQrCard>

      {saved ? (
        <KarQrCard className="border-[var(--kq-ok)] bg-[color-mix(in_srgb,var(--kq-ok)_var(--kq-soft-alpha),var(--kq-surface))]">
          <div className="flex items-start gap-3">
            <CheckCircle2 className="mt-0.5 size-7 shrink-0 text-[var(--kq-ok)]" />
            <div className="min-w-0 flex-1">
              <p className="text-lg font-bold">{t("savedTitle")}</p>
              <p className="text-sm text-[var(--kq-muted)]">
                {t("savedText", {
                  time: formatDateTimeNl(saved.created_at),
                  counted: saved.total_counted,
                  expected: saved.total_expected,
                })}
              </p>
            </div>
            <button
              type="button"
              onClick={() => setSaved(null)}
              aria-label={t("close")}
              className="flex size-9 items-center justify-center rounded-[10px] text-[var(--kq-muted)] hover:bg-[var(--kq-raised)]"
            >
              <X className="size-5" />
            </button>
          </div>
        </KarQrCard>
      ) : null}

      {!context.kar_is_out ? (
        <p className="rounded-[12px] border border-[var(--kq-border)] bg-[color-mix(in_srgb,var(--kq-info)_var(--kq-soft-alpha),transparent)] px-4 py-3 text-sm text-[var(--kq-info)]">
          {t("inWarehouseNotice")}
        </p>
      ) : null}

      {/* The products of the kar. */}
      <section className="flex flex-col gap-3">
        <div className="flex items-baseline justify-between">
          <h2 className="text-lg font-bold">{t("products")}</h2>
          <span className="text-sm text-[var(--kq-muted)]">{t("countedOf", { done: countedLines, total: context.lines.length })}</span>
        </div>
        {context.lines.length === 0 ? (
          <KarQrCard className="text-center text-[var(--kq-muted)]">{t("emptyList")}</KarQrCard>
        ) : (
          context.lines.map((line) => (
            <ProductCard
              key={line.product_id}
              name={line.name}
              image={line.has_image ? karInventoryProductImageUrl(line.product_id, token) : null}
              expected={line.expected}
              value={counts[line.product_id] ?? null}
              onChange={(value) => setCount(line.product_id, value)}
            />
          ))
        )}

        {/* Products the team found in the kar that aren't on the list. */}
        {extras.map((extra) => (
          <ProductCard
            key={`extra-${extra.product.id}`}
            name={extra.product.name}
            image={extra.product.has_image ? karInventoryProductImageUrl(extra.product.id, token) : null}
            expected={null}
            value={extra.counted}
            onChange={(value) =>
              setExtras((current) =>
                current.map((item) => (item.product.id === extra.product.id ? { ...item, counted: value } : item)),
              )
            }
            onRemove={() => setExtras((current) => current.filter((item) => item.product.id !== extra.product.id))}
          />
        ))}

        {isAddingExtra ? (
          <KarQrCard className="flex flex-col gap-3">
            <div className="flex items-center justify-between">
              <span className="font-semibold">{t("extraTitle")}</span>
              <button
                type="button"
                onClick={() => setIsAddingExtra(false)}
                aria-label={t("close")}
                className="flex size-9 items-center justify-center rounded-[10px] text-[var(--kq-muted)] hover:bg-[var(--kq-raised)]"
              >
                <X className="size-5" />
              </button>
            </div>
            {productOptions === null ? (
              <Loader2 className="mx-auto size-6 animate-spin text-[var(--kq-muted)]" />
            ) : (
              <Typeahead
                items={productOptions}
                getKey={(item) => item.id}
                getText={(item) => item.name}
                renderItem={(item) => <span className="py-1">{item.name}</span>}
                isDisabled={(item) => takenIds.has(item.id)}
                onSelect={(item) => {
                  setExtras((current) => [...current, { product: item, counted: 1 }]);
                  setIsAddingExtra(false);
                }}
                placeholder={t("extraSearch")}
                emptyText={t("extraNone")}
                autoFocus
              />
            )}
          </KarQrCard>
        ) : (
          <button
            type="button"
            onClick={openExtra}
            className="flex h-[52px] items-center justify-center gap-2 rounded-[14px] border-2 border-dashed border-[var(--kq-border)] font-semibold text-[var(--kq-muted)] transition hover:border-[var(--kq-teal)] hover:text-[var(--kq-teal)]"
          >
            <PackagePlus className="size-5" />
            {t("extraAdd")}
          </button>
        )}
      </section>

      {/* Who counted, and a remark. */}
      <KarQrCard className="flex flex-col gap-4">
        <label className="flex flex-col gap-2">
          <span className="text-sm font-semibold text-[var(--kq-muted)]">
            {t("name")} <span className="text-[var(--kq-danger)]">*</span>
          </span>
          <input
            value={name}
            onChange={(event) => setName(event.target.value)}
            maxLength={100}
            autoComplete="name"
            className="h-[52px] rounded-[10px] border border-[var(--kq-border)] bg-[var(--kq-raised)] px-4 text-base outline-none focus:border-[var(--kq-teal)]"
          />
        </label>
        <label className="flex flex-col gap-2">
          <span className="text-sm font-semibold text-[var(--kq-muted)]">{t("remark")}</span>
          <textarea
            value={remark}
            onChange={(event) => setRemark(event.target.value)}
            maxLength={2000}
            rows={3}
            placeholder={t("remarkPlaceholder")}
            className="rounded-[10px] border border-[var(--kq-border)] bg-[var(--kq-raised)] px-4 py-3 text-base outline-none placeholder:text-[var(--kq-faint)] focus:border-[var(--kq-teal)]"
          />
        </label>
      </KarQrCard>

      <KarInventoryHistory history={context.history} />

      {/* Sticky save bar at the bottom of the screen. */}
      <div className="fixed inset-x-0 bottom-0 z-30 border-t border-[var(--kq-border)] bg-[var(--kq-surface)]/95 backdrop-blur">
        <div className="mx-auto flex max-w-3xl flex-col gap-2 px-4 py-3">
          {error ? <p className="text-sm font-medium text-[var(--kq-danger)]">{error}</p> : null}
          {askZero ? (
            <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
              <p className="flex-1 text-sm">{t("askZero", { count: uncounted })}</p>
              <div className="flex gap-2">
                <button
                  type="button"
                  onClick={() => setAskZero(false)}
                  className="h-[52px] flex-1 rounded-[12px] border border-[var(--kq-border)] px-4 font-semibold sm:flex-none"
                >
                  {t("keepCounting")}
                </button>
                <button
                  type="button"
                  onClick={() => save(true)}
                  className="h-[52px] flex-1 rounded-[12px] bg-[var(--kq-warn)] px-4 font-semibold text-white sm:flex-none"
                >
                  {t("saveWithZero")}
                </button>
              </div>
            </div>
          ) : (
            <div className="flex items-center gap-3">
              <div className="min-w-0 flex-1">
                <p className="text-sm text-[var(--kq-muted)]">{t("countedOf", { done: countedLines, total: context.lines.length })}</p>
                <p className="font-semibold">{t("piecesOf", { counted: totalCounted, expected: totalExpected })}</p>
              </div>
              <button
                type="button"
                onClick={() => save(false)}
                disabled={isSaving}
                className="flex h-[52px] items-center gap-2 rounded-[12px] bg-[var(--kq-teal)] px-6 text-lg font-semibold text-white transition active:scale-[0.99] disabled:opacity-50"
              >
                {isSaving ? <Loader2 className="size-5 animate-spin" /> : <Save className="size-5" />}
                {t("save")}
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

/** "Onderweg sinds …" (teal) or "In het magazijn" (muted). */
function StatusPill({ isOut, since }: { isOut: boolean; since: string | null }) {
  const t = useTranslations("stockMaster.publicInventory");
  const Icon = isOut ? Truck : Warehouse;
  return (
    <span
      className={cn(
        "flex shrink-0 items-center gap-1.5 rounded-full px-3 py-1.5 text-xs font-semibold",
        isOut
          ? "bg-[color-mix(in_srgb,var(--kq-teal)_var(--kq-soft-alpha),transparent)] text-[var(--kq-teal)]"
          : "bg-[var(--kq-raised)] text-[var(--kq-muted)]",
      )}
      title={since ? formatDateTimeNl(since) : undefined}
    >
      <Icon className="size-4" />
      {isOut ? t("statusOut") : t("statusWarehouse")}
    </span>
  );
}

interface ProductCardProps {
  name: string;
  image: string | null;
  /** What left with the kar (null = an extra product). */
  expected: number | null;
  value: number | null;
  onChange: (value: number | null) => void;
  onRemove?: () => void;
}

/** One product: picture, name, "left with the kar" chip, −/+ stepper, difference badge. */
function ProductCard({ name, image, expected, value, onChange, onRemove }: ProductCardProps) {
  const t = useTranslations("stockMaster.publicInventory");
  const isCounted = value !== null;

  return (
    <div
      className={cn(
        "flex flex-col gap-3 rounded-[14px] border bg-[var(--kq-surface)] p-3 transition sm:flex-row sm:items-center",
        isCounted ? "border-[var(--kq-teal)]/60" : "border-[var(--kq-border)]",
      )}
    >
      <div className="flex min-w-0 flex-1 items-center gap-3">
        <div className="flex size-14 shrink-0 items-center justify-center overflow-hidden rounded-[10px] border border-[var(--kq-border)] bg-white">
          {image ? (
            // eslint-disable-next-line @next/next/no-img-element -- token-protected backend picture, not a static asset
            <img src={image} alt="" className="size-full object-contain" loading="lazy" />
          ) : (
            <Package className="size-7 text-[var(--kq-faint)]" />
          )}
        </div>
        <div className="min-w-0 flex-1">
          <p className="truncate text-base font-semibold">{name}</p>
          <div className="mt-1 flex flex-wrap items-center gap-1.5">
            {expected === null ? (
              <span className="rounded-full bg-[color-mix(in_srgb,var(--kq-info)_var(--kq-soft-alpha),transparent)] px-2 py-0.5 text-xs font-semibold text-[var(--kq-info)]">
                {t("extraBadge")}
              </span>
            ) : (
              <span className="rounded-full bg-[var(--kq-raised)] px-2 py-0.5 text-xs text-[var(--kq-muted)]">
                {t("leftWithKar")} <b className="text-[var(--kq-text)]">{expected}</b>
              </span>
            )}
            {expected !== null && isCounted ? <DiffBadge expected={expected} counted={value} /> : null}
          </div>
        </div>
        {onRemove ? (
          <button
            type="button"
            onClick={onRemove}
            aria-label={t("remove")}
            className="flex size-9 shrink-0 items-center justify-center rounded-[10px] text-[var(--kq-muted)] hover:bg-[var(--kq-raised)] hover:text-[var(--kq-danger)]"
          >
            <X className="size-5" />
          </button>
        ) : null}
      </div>

      {/* The stepper: big −, the number (typeable), big +. */}
      <div className="flex items-center gap-2 self-stretch sm:self-auto">
        <button
          type="button"
          onClick={() => onChange(Math.max((value ?? 0) - 1, 0))}
          aria-label={t("less")}
          className="flex size-[52px] shrink-0 items-center justify-center rounded-[12px] border border-[var(--kq-border)] bg-[var(--kq-raised)] active:scale-95"
        >
          <Minus className="size-6" />
        </button>
        <input
          value={value ?? ""}
          onChange={(event) => {
            const digits = event.target.value.replace(/\D/g, "").slice(0, 5);
            onChange(digits === "" ? null : Number(digits));
          }}
          onFocus={(event) => event.target.select()}
          inputMode="numeric"
          placeholder="–"
          aria-label={t("countFor", { name })}
          className="h-[52px] w-full min-w-0 flex-1 rounded-[12px] border border-[var(--kq-border)] bg-[var(--kq-raised)] text-center text-2xl font-bold outline-none placeholder:text-[var(--kq-faint)] focus:border-[var(--kq-teal)] sm:w-20 sm:flex-none"
        />
        <button
          type="button"
          onClick={() => onChange((value ?? 0) + 1)}
          aria-label={t("more")}
          className="flex size-[52px] shrink-0 items-center justify-center rounded-[12px] bg-[var(--kq-teal)] text-white active:scale-95"
        >
          <Plus className="size-6" />
        </button>
      </div>
    </div>
  );
}

/** Green "Alles terug", orange "2 minder", blue "1 meer". */
export function DiffBadge({ expected, counted }: { expected: number; counted: number }) {
  const t = useTranslations("stockMaster.publicInventory");
  const difference = counted - expected;
  const colour = difference === 0 ? "var(--kq-ok)" : difference < 0 ? "var(--kq-warn)" : "var(--kq-info)";
  const text =
    difference === 0 ? t("diffEqual") : difference < 0 ? t("diffLess", { count: -difference }) : t("diffMore", { count: difference });
  return (
    <span
      style={{ ["--diff" as string]: colour }}
      className="rounded-full bg-[color-mix(in_srgb,var(--diff)_var(--kq-soft-alpha),transparent)] px-2 py-0.5 text-xs font-semibold text-[var(--diff)]"
    >
      {text}
    </span>
  );
}
