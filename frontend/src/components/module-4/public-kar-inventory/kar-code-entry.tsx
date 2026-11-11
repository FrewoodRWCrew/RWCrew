"use client";

// Kar inventaris, step 1: the team types the kar's lock code (the Karcode on
// KarManagement — only the team knows it). Big centred code box with a
// numeric keyboard, shakes on a wrong code; after 5 wrong codes the kar waits
// 15 minutes (countdown). Without a kar number in the QR link (an old or
// hand-typed address) the kar number is asked too.

import { useEffect, useState, type FormEvent } from "react";
import { useTranslations } from "next-intl";
import { KeyRound, Loader2, LockKeyhole } from "lucide-react";

import { ApiError, unlockKarInventory } from "@/lib/api";
import { cn } from "@/lib/utils";
import { KarQrCard } from "@/components/shared/kar-qr/kar-qr-shell";

interface KarCodeEntryProps {
  /** The kar from the QR code (null = ask it). */
  karNumber: string | null;
  /** Shown above the box, e.g. "your session ended". */
  notice?: string | null;
  onUnlocked: (karNumber: string, token: string) => void;
}

export function KarCodeEntry({ karNumber, notice, onUnlocked }: KarCodeEntryProps) {
  const t = useTranslations("stockMaster.publicInventory");
  const [typedKar, setTypedKar] = useState("");
  const [code, setCode] = useState("");
  const [isBusy, setIsBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  // Bumped on every wrong code so the shake animation restarts.
  const [shakeCount, setShakeCount] = useState(0);
  // While the kar is locked: the moment it opens again, and a ticking "now".
  const [lockedUntil, setLockedUntil] = useState<number | null>(null);
  const [now, setNow] = useState(() => Date.now());

  // Tick every second while locked (state only changes from the timer's callback).
  useEffect(() => {
    if (lockedUntil === null) return;
    const timer = window.setInterval(() => setNow(Date.now()), 1000);
    return () => window.clearInterval(timer);
  }, [lockedUntil]);

  const secondsLeft = lockedUntil === null ? 0 : Math.max(Math.ceil((lockedUntil - now) / 1000), 0);
  const isLocked = secondsLeft > 0;
  const kar = (karNumber ?? typedKar).trim();

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!kar || !code.trim() || isBusy || isLocked) return;
    setIsBusy(true);
    setError(null);
    try {
      const result = await unlockKarInventory(kar, code.trim());
      onUnlocked(result.kar_nummer, result.token);
    } catch (caught) {
      const [key, param] = caught instanceof ApiError ? caught.message.split("|") : ["network"];
      if (key === "too_many_tries") {
        // Locked: count down from the seconds the backend gave.
        const seconds = Number(param) || 60;
        const start = Date.now();
        setNow(start);
        setLockedUntil(start + seconds * 1000);
        setError(null);
      } else {
        setError(key === "wrong_code" || key === "no_code" ? t(`errors.${key}`) : t("errors.network"));
      }
      setShakeCount((count) => count + 1);
      setCode("");
    } finally {
      setIsBusy(false);
    }
  }

  const minutes = Math.floor(secondsLeft / 60);
  const seconds = String(secondsLeft % 60).padStart(2, "0");

  return (
    <div className="flex flex-col items-center pt-4">
      {/* Big lock badge in StockMaster's teal. */}
      <div className="mb-5 flex size-20 items-center justify-center rounded-[22px] bg-[var(--kq-teal)] text-white shadow-[0_16px_40px_-12px_var(--kq-teal)]">
        <LockKeyhole className="size-10" />
      </div>
      <h1 className="text-center text-2xl font-bold">{t("codeTitle")}</h1>
      <p className="mt-2 max-w-sm text-center text-[var(--kq-muted)]">{t("codeExplanation")}</p>

      <KarQrCard className="mt-6 w-full max-w-sm p-5">
        {notice ? (
          <p className="mb-4 rounded-[10px] bg-[color-mix(in_srgb,var(--kq-info)_var(--kq-soft-alpha),transparent)] px-3 py-2 text-sm text-[var(--kq-info)]">
            {notice}
          </p>
        ) : null}
        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          {karNumber ? null : (
            <label className="flex flex-col gap-2">
              <span className="text-sm font-semibold text-[var(--kq-muted)]">{t("karNumber")}</span>
              <input
                value={typedKar}
                onChange={(event) => setTypedKar(event.target.value)}
                autoCapitalize="characters"
                placeholder="B001"
                className="h-[52px] rounded-[10px] border border-[var(--kq-border)] bg-[var(--kq-raised)] px-4 text-lg font-semibold uppercase outline-none focus:border-[var(--kq-teal)]"
              />
            </label>
          )}
          <label className="flex flex-col gap-2">
            <span className="text-sm font-semibold text-[var(--kq-muted)]">{t("code")}</span>
            <div key={shakeCount} className={cn(shakeCount > 0 && "kq-shake")}>
              <input
                value={code}
                onChange={(event) => {
                  setCode(event.target.value.replace(/\s/g, ""));
                  setError(null);
                }}
                inputMode="numeric"
                autoComplete="one-time-code"
                autoFocus
                maxLength={20}
                disabled={isLocked}
                placeholder="• • • •"
                aria-invalid={error !== null}
                className={cn(
                  "h-16 w-full rounded-[12px] border-2 bg-[var(--kq-raised)] text-center text-4xl font-bold tracking-[0.4em] outline-none placeholder:text-[var(--kq-faint)] disabled:opacity-50",
                  error ? "border-[var(--kq-danger)]" : "border-[var(--kq-border)] focus:border-[var(--kq-teal)]",
                )}
              />
            </div>
          </label>

          {error ? <p className="text-center text-sm font-medium text-[var(--kq-danger)]">{error}</p> : null}
          {isLocked ? (
            <p className="text-center text-sm font-medium text-[var(--kq-warn)]">
              {t("errors.too_many_tries", { time: `${minutes}:${seconds}` })}
            </p>
          ) : null}

          <button
            type="submit"
            disabled={!kar || !code || isBusy || isLocked}
            className="flex h-[52px] items-center justify-center gap-2 rounded-[12px] bg-[var(--kq-teal)] text-lg font-semibold text-white transition active:scale-[0.99] disabled:opacity-40"
          >
            {isBusy ? <Loader2 className="size-5 animate-spin" /> : <KeyRound className="size-5" />}
            {t("open")}
          </button>
        </form>
      </KarQrCard>
      <p className="mt-4 max-w-sm text-center text-xs text-[var(--kq-faint)]">{t("codeHint")}</p>
    </div>
  );
}
